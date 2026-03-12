import atexit
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass


APP_CONFIG_FILE = "config.json"


@dataclass(frozen=True)
class TerminalProfile:
    key: str
    display_name: str
    jar_file: str
    download_url: str
    launch_mode: str
    java_min_version: int
    supports_server_settings: bool = False

    @property
    def jar_path(self):
        return os.path.abspath(self.jar_file)

    @property
    def jar_directory(self):
        return os.path.dirname(self.jar_path) or os.getcwd()


TERMINAL_PROFILES = {
    "v2": TerminalProfile(
        key="v2",
        display_name="ThetaTerminal v2",
        jar_file="ThetaTerminal.jar",
        download_url="https://download-stable.thetadata.us/ThetaTerminal.jar",
        launch_mode="cli_credentials",
        java_min_version=8,
        supports_server_settings=True,
    ),
    "v3": TerminalProfile(
        key="v3",
        display_name="ThetaTerminal v3",
        jar_file="ThetaTerminalv3.jar",
        download_url="https://download-unstable.thetadata.us/ThetaTerminalv3.jar",
        launch_mode="creds_file",
        java_min_version=21,
        supports_server_settings=False,
    ),
}


class DownloadProgressTracker:
    def __init__(self, callback=None):
        self.callback = callback
        self.total_size = 0
        self.downloaded = 0

    def __call__(self, count, block_size, total_size):
        self.total_size = total_size
        self.downloaded = count * block_size
        if self.total_size > 0:
            self.downloaded = min(self.downloaded, self.total_size)

        percentage = 0
        if self.total_size > 0:
            percentage = int(self.downloaded * 100 / self.total_size)

        if self.callback:
            self.callback(percentage, self.downloaded, self.total_size)


class TerminalManager:
    def __init__(self, profile):
        self.profile = profile
        self.config_file = APP_CONFIG_FILE
        self.username = ""
        self.password = ""
        self.process = None
        self.running = False
        self.log_callback = None
        self.download_progress_callback = None
        self.download_thread = None
        self.is_downloading = False
        self.download_complete_callback = None
        self.start_after_download = False
        self.auto_start_complete_callback = None

        self.mdds_regions = ["MDDS_NJ_HOSTS", "MDDS_STAGE_HOSTS", "MDDS_DEV_HOSTS"]
        self.fpss_regions = ["FPSS_NJ_HOSTS", "FPSS_STAGE_HOSTS", "FPSS_DEV_HOSTS"]
        self.current_mdds_region = "MDDS_NJ_HOSTS"
        self.current_fpss_region = "FPSS_NJ_HOSTS"

        self.logs_folder = ""
        self.config_folder = ""

        self.load_config()
        self._refresh_runtime_paths()
        self._read_properties_file()

        atexit.register(self.cleanup)

    def cleanup(self):
        """Clean up resources when the application exits."""
        try:
            if self.process and self.process.poll() is None:
                self.process.kill()
                self.process.wait(timeout=2.0)
        except Exception:
            pass
        finally:
            self.running = False

    def _load_full_config(self):
        if not os.path.exists(self.config_file):
            return {}

        try:
            with open(self.config_file, "r", encoding="utf-8") as file:
                data = json.load(file)
                return data if isinstance(data, dict) else {}
        except Exception as exc:
            self._log(f"Error loading config: {exc}")
            return {}

    def _save_full_config(self, config):
        try:
            with open(self.config_file, "w", encoding="utf-8") as file:
                json.dump(config, file, indent=2)
        except Exception as exc:
            self._log(f"Error saving config: {exc}")

    def load_config(self):
        """Load saved credentials for this terminal profile."""
        config = self._load_full_config()

        if self.profile.key in config and isinstance(config[self.profile.key], dict):
            profile_config = config[self.profile.key]
            self.username = profile_config.get("username", "")
            self.password = profile_config.get("password", "")
            return

        if self.profile.key == "v2":
            self.username = config.get("username", "")
            self.password = config.get("password", "")

    def save_config(self):
        """Save credentials for this terminal profile."""
        config = self._load_full_config()

        profile_config = config.get(self.profile.key, {})
        if not isinstance(profile_config, dict):
            profile_config = {}

        profile_config.update({"username": self.username, "password": self.password})
        config[self.profile.key] = profile_config
        config["selected_version"] = self.profile.key

        self._save_full_config(config)

    def get_selected_version(self):
        config = self._load_full_config()
        return config.get("selected_version", "v2")

    def set_selected_version(self, version_key):
        config = self._load_full_config()
        config["selected_version"] = version_key
        self._save_full_config(config)

    def _log(self, message):
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def check_jar_file(self):
        return os.path.exists(self.profile.jar_path)

    def _refresh_runtime_paths(self):
        if self.profile.key == "v2":
            self.logs_folder = os.path.join(
                os.path.expanduser("~"), "ThetaData", "ThetaTerminal", "logs"
            )
            self.config_folder = os.path.join(
                os.path.expanduser("~"), "ThetaData", "ThetaTerminal"
            )
        else:
            self.config_folder = self.profile.jar_directory
            self.logs_folder = self._resolve_v3_log_directory()

    def _resolve_v3_log_directory(self):
        jar_directory = self.profile.jar_directory
        default_logs_directory = os.path.join(jar_directory, "logs")

        for config_path in self._discover_v3_config_files():
            try:
                with open(config_path, "r", encoding="utf-8", errors="ignore") as file:
                    for line in file:
                        match = re.match(r"\s*log_directory\s*[:=]\s*(.+?)\s*$", line)
                        if not match:
                            continue

                        log_directory = match.group(1).strip().strip('"').strip("'")
                        if not os.path.isabs(log_directory):
                            log_directory = os.path.join(jar_directory, log_directory)
                        return os.path.abspath(log_directory)
            except OSError:
                continue

        if os.path.exists(default_logs_directory):
            return default_logs_directory

        return jar_directory

    def _discover_v3_config_files(self):
        jar_directory = self.profile.jar_directory
        if not os.path.isdir(jar_directory):
            return []

        preferred_names = {
            "config.properties",
            "thetaterminalv3.properties",
            "thetaterminal.properties",
            "config.ini",
            "config.yaml",
            "config.yml",
            "config.json",
        }
        discovered = []

        for name in os.listdir(jar_directory):
            lower_name = name.lower()
            full_path = os.path.join(jar_directory, name)
            if not os.path.isfile(full_path):
                continue
            if lower_name == "creds.txt":
                continue
            if lower_name in preferred_names or (
                "config" in lower_name
                and lower_name.endswith(
                    (".properties", ".conf", ".ini", ".yaml", ".yml", ".json", ".txt")
                )
            ):
                discovered.append(full_path)

        return sorted(discovered)

    def _download_progress(self, percentage, downloaded, total_size):
        if self.download_progress_callback:
            self.download_progress_callback(percentage, downloaded, total_size)

    def _download_jar_file_async(self):
        if self.is_downloading:
            return

        self.is_downloading = True
        self._log(f"Starting {self.profile.jar_file} download...")

        self.download_thread = threading.Thread(target=self.download_jar_file, daemon=True)
        self.download_thread.start()

    def _notify_download_complete(self, success):
        self.is_downloading = False

        if self.download_complete_callback:
            try:
                self.download_complete_callback(success)
            except Exception as exc:
                self._log(f"Error in download complete notification: {exc}")

        if not success:
            self.start_after_download = False
            return

        if self.start_after_download:
            self.start_after_download = False

            def delayed_start():
                time.sleep(1.0)
                self._log(
                    f"Auto-starting {self.profile.display_name} after download completes..."
                )
                start_success = self.start_terminal(self.username, self.password)
                if not start_success:
                    self._log(
                        f"Failed to auto-start {self.profile.display_name}. Please try Start again."
                    )

                if self.auto_start_complete_callback:
                    try:
                        self.auto_start_complete_callback(start_success)
                    except Exception as exc:
                        self._log(f"Error in auto-start complete notification: {exc}")

            threading.Thread(target=delayed_start, daemon=True).start()

    def download_jar_file(self):
        try:
            self._log(f"Downloading {self.profile.jar_file}...")

            os.makedirs(self.profile.jar_directory, exist_ok=True)
            progress_tracker = DownloadProgressTracker(self._download_progress)
            urllib.request.urlretrieve(
                self.profile.download_url,
                self.profile.jar_path,
                reporthook=progress_tracker,
            )

            if self.download_progress_callback and progress_tracker.total_size > 0:
                self.download_progress_callback(
                    100, progress_tracker.total_size, progress_tracker.total_size
                )

            self._log(f"{self.profile.jar_file} downloaded successfully.")
            self._refresh_runtime_paths()
            time.sleep(0.5)
            self._notify_download_complete(True)
            return True
        except Exception as exc:
            self._log(f"Error downloading {self.profile.jar_file}: {exc}")
            self._notify_download_complete(False)
            return False

    def _get_java_major_version(self):
        try:
            result = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
        except FileNotFoundError:
            return None
        except Exception as exc:
            self._log(f"Unable to determine Java version: {exc}")
            return None

        output = f"{result.stdout}\n{result.stderr}"
        match = re.search(r'version\s+"(?P<version>\d+)(?:\.\d+)?', output)
        if match:
            return int(match.group("version"))

        match = re.search(r"openjdk\s+(?P<version>\d+)", output, re.IGNORECASE)
        if match:
            return int(match.group("version"))

        return None

    def _validate_java_requirement(self):
        java_major = self._get_java_major_version()
        if java_major is None:
            self._log(
                f"Java could not be found. {self.profile.display_name} requires Java {self.profile.java_min_version}+."
            )
            return False

        if java_major < self.profile.java_min_version:
            self._log(
                f"Java {self.profile.java_min_version}+ is required for {self.profile.display_name}. Detected Java {java_major}."
            )
            return False

        return True

    def _write_v3_creds_file(self, username, password):
        creds_path = os.path.join(self.profile.jar_directory, "creds.txt")
        os.makedirs(self.profile.jar_directory, exist_ok=True)

        with open(creds_path, "w", encoding="utf-8") as file:
            file.write(f"{username}\n{password}\n")

        return creds_path

    def _build_launch_command(self, username, password):
        jar_name = os.path.basename(self.profile.jar_path)

        if self.profile.launch_mode == "cli_credentials":
            return ["java", "-jar", jar_name, username, password]

        self._write_v3_creds_file(username, password)
        return ["java", "-jar", jar_name]

    def start_terminal(self, username, password):
        """Start the configured terminal process."""
        if self.running:
            self._log(f"{self.profile.display_name} is already running.")
            return False

        if self.is_downloading:
            self._log(
                f"{self.profile.jar_file} is still downloading. Please wait for the download to finish."
            )
            return False

        self.username = username
        self.password = password
        self.save_config()

        if not os.path.exists(self.profile.jar_path):
            self._log(f"{self.profile.jar_file} not found. Starting download...")
            self.start_after_download = True
            self._download_jar_file_async()
            return False

        if not self._validate_java_requirement():
            return False

        try:
            cmd = self._build_launch_command(username, password)

            if sys.platform.startswith("win"):
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = subprocess.SW_HIDE

                self.process = subprocess.Popen(
                    cmd,
                    cwd=self.profile.jar_directory,
                    startupinfo=startup_info,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    bufsize=1,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                self.process = subprocess.Popen(
                    cmd,
                    cwd=self.profile.jar_directory,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    errors="replace",
                    bufsize=1,
                    preexec_fn=os.setsid,
                )

            self.running = True
            self._refresh_runtime_paths()
            self._read_properties_file()

            self._log(f"{self.profile.display_name} started with PID: {self.process.pid}")
            self._log("Terminal started successfully.")

            self.output_thread = threading.Thread(target=self._read_output, daemon=True)
            self.output_thread.start()
            return True
        except Exception as exc:
            self._log(f"Error starting terminal: {exc}")
            return False

    def _find_matching_java_processes_windows(self):
        jar_name = os.path.basename(self.profile.jar_path).replace("'", "''")
        command = (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -match '^java(|w)?\\.exe$' -and $_.CommandLine -like '*"
            + jar_name
            + "*' } | "
            "Select-Object -ExpandProperty ProcessId"
        )

        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            pids = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if line.isdigit():
                    pids.append(int(line))
            return pids
        except Exception as exc:
            self._log(f"Error checking Java processes: {exc}")
            return []

    def stop_terminal(self):
        """Stop the terminal process if it is running."""
        if not self.running or not self.process:
            self._log(f"Stop called but {self.profile.display_name} is not running.")
            return False

        pid = self.process.pid
        self._log(f"Stopping {self.profile.display_name} with PID: {pid}")

        try:
            if sys.platform.startswith("win"):
                result = subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=10.0,
                )
                if result.returncode != 0 and result.stderr.strip():
                    self._log(result.stderr.strip())

                time.sleep(1.0)

                remaining_pids = self._find_matching_java_processes_windows()
                for remaining_pid in remaining_pids:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(remaining_pid)],
                        capture_output=True,
                        text=True,
                        timeout=5.0,
                    )

                time.sleep(0.5)
                remaining_pids = self._find_matching_java_processes_windows()
                self.running = False

                if remaining_pids:
                    self._log(
                        f"Warning: matching Java processes are still running for {self.profile.jar_file}: {remaining_pids}"
                    )
                    return False

                self._log(f"{self.profile.display_name} stopped successfully.")
                return True

            self.process.terminate()
            try:
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5.0)

            self.running = False
            self._log(f"{self.profile.display_name} stopped successfully.")
            return True
        except Exception as exc:
            self._log(f"Error in stop_terminal: {exc}")
            self.running = False
            return False
        finally:
            self.process = None

    def is_running(self):
        if not self.running:
            return False

        if self.process and self.process.poll() is not None:
            self.running = False
            self.process = None
            return False

        return self.running

    def get_downloading_status(self):
        return self.is_downloading

    def set_log_callback(self, callback):
        self.log_callback = callback

    def set_download_progress_callback(self, callback):
        self.download_progress_callback = callback

    def set_download_complete_callback(self, callback):
        self.download_complete_callback = callback

    def set_auto_start_complete_callback(self, callback):
        self.auto_start_complete_callback = callback

    def _read_output(self):
        try:
            if self.process and self.process.stdout:
                for line in self.process.stdout:
                    message = line.strip()
                    if message:
                        self._log(message)
        except Exception as exc:
            self._log(f"Error reading output: {exc}")
        finally:
            if self.process and self.process.poll() is not None:
                self.running = False
                self._refresh_runtime_paths()
                self._log("Process ended.")

    def open_logs_folder(self):
        self._refresh_runtime_paths()

        if os.path.exists(self.logs_folder):
            self._open_folder(self.logs_folder)
            self._log(f"Opening logs folder: {self.logs_folder}")
            return True

        self._log(f"Logs folder not found: {self.logs_folder}")
        return False

    def open_config_folder(self):
        self._refresh_runtime_paths()

        if os.path.exists(self.config_folder):
            self._open_folder(self.config_folder)
            self._log(f"Opening config folder: {self.config_folder}")
            return True

        self._log(f"Config folder not found: {self.config_folder}")
        return False

    def _open_folder(self, folder_path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder_path)
            elif sys.platform.startswith("darwin"):
                subprocess.call(["open", folder_path])
            else:
                subprocess.call(["xdg-open", folder_path])
            return True
        except Exception as exc:
            self._log(f"Error opening folder: {exc}")
            return False

    def _read_properties_file(self):
        if not self.profile.supports_server_settings:
            return

        properties_path = os.path.join(self.config_folder, "config_0.properties")
        if not os.path.exists(properties_path):
            return

        try:
            with open(properties_path, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("MDDS_REGION="):
                        self.current_mdds_region = line.split("=", 1)[1]
                    elif line.startswith("FPSS_REGION="):
                        self.current_fpss_region = line.split("=", 1)[1]

            self._log(
                "Current server settings loaded: "
                f"MDDS={self.current_mdds_region}, FPSS={self.current_fpss_region}"
            )
        except Exception as exc:
            self._log(f"Error reading properties file: {exc}")

    def update_server_regions(self, mdds_region, fpss_region):
        if not self.profile.supports_server_settings:
            self._log("Server region editing is only available for ThetaTerminal v2.")
            return False

        properties_path = os.path.join(self.config_folder, "config_0.properties")

        if not os.path.exists(properties_path):
            self._log(
                "Properties file not found. It will be created when ThetaTerminal runs for the first time."
            )
            self.current_mdds_region = mdds_region
            self.current_fpss_region = fpss_region
            return False

        try:
            with open(properties_path, "r", encoding="utf-8") as file:
                lines = file.readlines()

            updated_lines = []
            for line in lines:
                stripped_line = line.strip()
                if stripped_line.startswith("MDDS_REGION="):
                    updated_lines.append(f"MDDS_REGION={mdds_region}\n")
                elif stripped_line.startswith("FPSS_REGION="):
                    updated_lines.append(f"FPSS_REGION={fpss_region}\n")
                else:
                    updated_lines.append(line)

            with open(properties_path, "w", encoding="utf-8") as file:
                file.writelines(updated_lines)

            self.current_mdds_region = mdds_region
            self.current_fpss_region = fpss_region
            self._log(
                f"Server settings updated: MDDS={mdds_region}, FPSS={fpss_region}"
            )
            return True
        except Exception as exc:
            self._log(f"Error updating properties file: {exc}")
            return False

    def get_server_regions(self):
        return {
            "mdds_region": self.current_mdds_region,
            "fpss_region": self.current_fpss_region,
            "mdds_options": self.mdds_regions,
            "fpss_options": self.fpss_regions,
        }