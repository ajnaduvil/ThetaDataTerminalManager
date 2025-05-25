import os
import json
import subprocess
import urllib.request
import threading
import sys
import atexit
import time


class DownloadProgressTracker:
    def __init__(self, callback=None):
        self.callback = callback
        self.total_size = 0
        self.downloaded = 0

    def __call__(self, count, block_size, total_size):
        self.total_size = total_size
        self.downloaded += block_size
        percentage = 0
        if self.total_size > 0:
            percentage = int(self.downloaded * 100 / self.total_size)
        if self.callback:
            self.callback(percentage, self.downloaded, self.total_size)


class TerminalManager:
    def __init__(self):
        self.config_file = "config.json"
        self.jar_file = "ThetaTerminal.jar"
        self.download_url = "https://download-stable.thetadata.us/ThetaTerminal.jar"
        self.username = ""
        self.password = ""
        self.process = None
        self.running = False
        self.log_callback = None
        self.download_progress_callback = None
        self.download_thread = None
        self.is_downloading = False
        self.download_complete_callback = None
        self.start_after_download = False  # Flag to auto-start after download
        self.auto_start_complete_callback = (
            None  # Callback for when auto-start completes
        )

        # Paths for logs and config folders
        self.logs_folder = os.path.join(
            os.path.expanduser("~"), "ThetaData", "ThetaTerminal", "logs"
        )
        self.config_folder = os.path.dirname(
            os.path.join(
                os.path.expanduser("~"),
                "ThetaData",
                "ThetaTerminal",
                "config_0.properties",
            )
        )

        # Server region options
        self.mdds_regions = ["MDDS_NJ_HOSTS", "MDDS_STAGE_HOSTS", "MDDS_DEV_HOSTS"]
        self.fpss_regions = ["FPSS_NJ_HOSTS", "FPSS_STAGE_HOSTS", "FPSS_DEV_HOSTS"]
        self.current_mdds_region = "MDDS_NJ_HOSTS"
        self.current_fpss_region = "FPSS_NJ_HOSTS"

        # Read current settings from properties file if it exists
        self._read_properties_file()

        # Load configuration if it exists
        self.load_config()

        # Register cleanup function to ensure processes are terminated on exit
        atexit.register(self.cleanup)

    def cleanup(self):
        """Clean up resources when the application exits"""
        try:
            if self.running and self.process:
                try:
                    # Force kill the process immediately during cleanup
                    self.process.kill()
                    self.process.wait(timeout=2.0)  # Wait briefly for cleanup
                except Exception:
                    pass
                self.running = False
        except Exception:
            # Ensure we don't propagate exceptions during cleanup
            pass

    def load_config(self):
        """Load username and password from config file if it exists"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    config = json.load(f)
                    self.username = config.get("username", "")
                    self.password = config.get("password", "")
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"Error loading config: {e}")
                else:
                    print(f"Error loading config: {e}")  # Fallback if no callback set

    def save_config(self):
        """Save username and password to config file"""
        try:
            with open(self.config_file, "w") as f:
                json.dump({"username": self.username, "password": self.password}, f)
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error saving config: {e}")
            else:
                print(f"Error saving config: {e}")  # Fallback if no callback set

    def check_jar_file(self):
        """Check if JAR file exists, download if not"""
        if not os.path.exists(self.jar_file):
            # Start async download
            self._download_jar_file_async()
            return False
        return True

    def _download_progress(self, percentage, downloaded, total_size):
        """Handle download progress updates"""
        if self.download_progress_callback:
            self.download_progress_callback(percentage, downloaded, total_size)

    def _download_jar_file_async(self):
        """Start asynchronous download of the JAR file"""
        if self.is_downloading:
            return

        self.is_downloading = True

        if self.log_callback:
            self.log_callback("Starting ThetaTerminal.jar download...")

        self.download_thread = threading.Thread(target=self.download_jar_file)
        self.download_thread.daemon = True
        self.download_thread.start()

    def _notify_download_complete(self):
        """Safely notify that download is complete"""
        self.is_downloading = False
        if self.download_complete_callback:
            try:
                self.download_complete_callback()
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"Error in download complete notification: {e}")

        # Check if we should auto-start the terminal after download
        if self.start_after_download:
            self.start_after_download = False  # Reset the flag
            # Small delay to ensure UI updates are complete

            def delayed_start():
                time.sleep(1.0)  # Give UI time to update
                if self.log_callback:
                    self.log_callback("Auto-starting terminal after download...")
                success = self.start_terminal(self.username, self.password)
                if not success and self.log_callback:
                    self.log_callback(
                        "Failed to auto-start terminal. Please try clicking Start again."
                    )

                # Notify UI that auto-start has completed (success or failure)
                if self.auto_start_complete_callback:
                    try:
                        self.auto_start_complete_callback(success)
                    except Exception as e:
                        if self.log_callback:
                            self.log_callback(
                                f"Error in auto-start complete notification: {e}"
                            )

            start_thread = threading.Thread(target=delayed_start, daemon=True)
            start_thread.start()

    def download_jar_file(self):
        """Download the JAR file from the URL with progress"""
        try:
            if self.log_callback:
                self.log_callback("Downloading ThetaTerminal.jar...")

            progress_tracker = DownloadProgressTracker(self._download_progress)
            urllib.request.urlretrieve(
                self.download_url, self.jar_file, reporthook=progress_tracker
            )

            # Ensure we send a final 100% progress update to hide the progress bar
            if self.download_progress_callback and progress_tracker.total_size > 0:
                self.download_progress_callback(
                    100, progress_tracker.total_size, progress_tracker.total_size
                )

            if self.log_callback:
                self.log_callback("Download completed successfully.")

            # Small delay to ensure UI updates happen in the correct order
            time.sleep(0.5)

            # Notify that download is complete using a safer method
            self._notify_download_complete()

            return True
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error downloading JAR file: {e}")

            # Notify that download process is finished, even if with error
            self._notify_download_complete()

            return False

    def start_terminal(self, username, password):
        """Start the terminal process with the given credentials"""
        if self.running:
            return False

        # Save credentials
        self.username = username
        self.password = password
        self.save_config()

        # Check if JAR file exists, download if not
        if not os.path.exists(self.jar_file):
            if self.log_callback:
                self.log_callback("ThetaTerminal.jar not found. Starting download...")
            self.start_after_download = True  # Set flag to auto-start after download
            self._download_jar_file_async()
            return False

        # Don't start if download is in progress
        if self.is_downloading:
            if self.log_callback:
                self.log_callback(
                    "Download in progress. Please wait until download completes."
                )
            return False

        # Start the process - simplified approach
        try:
            # Create the command
            cmd = ["java", "-jar", self.jar_file, username, password]

            # Process creation with proper signal handling support
            if sys.platform.startswith("win"):
                # Windows-specific process creation to ensure we can kill it
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startup_info.wShowWindow = subprocess.SW_HIDE

                # Use CREATE_NEW_PROCESS_GROUP to ensure clean process tree management
                self.process = subprocess.Popen(
                    cmd,
                    startupinfo=startup_info,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                )
            else:
                # On Unix systems - create new process group for clean killing
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    preexec_fn=os.setsid,  # Create new process group
                )

            self.running = True

            if self.log_callback:
                self.log_callback(f"JAR started with PID: {self.process.pid}")
                self.log_callback("Terminal started successfully.")

            # Start thread to read output (optional - can be removed if not needed)
            self.output_thread = threading.Thread(target=self._read_output)
            self.output_thread.daemon = True
            self.output_thread.start()

            return True
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error starting terminal: {e}")
            return False

    def _check_java_processes_running(self):
        """Check if any Java processes are still running with our JAR file"""
        if not sys.platform.startswith("win"):
            return False

        try:
            jar_name = os.path.basename(self.jar_file)
            result = subprocess.run(
                f'tasklist /FI "IMAGENAME eq java.exe" /FI "COMMANDLINE eq *{jar_name}*" /FO CSV',
                shell=True,
                capture_output=True,
                text=True,
                timeout=3.0,
            )

            # If output has more than just the header line, processes are running
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:  # More than just header
                if self.log_callback:
                    self.log_callback(
                        f"Found {len(lines)-1} java.exe processes still running with {jar_name}"
                    )
                return True
            return False
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error checking Java processes: {e}")
            return False

    def stop_terminal(self):
        """Stop the terminal process if it's running"""
        if not self.running or not self.process:
            if self.log_callback:
                self.log_callback("Stop called but terminal not running.")
            return False

        try:
            pid = self.process.pid
            if self.log_callback:
                self.log_callback(f"Stopping JAR process with PID: {pid}")

            # On Windows, Java processes are notoriously stubborn. Skip gentle methods.
            if sys.platform.startswith("win"):
                if self.log_callback:
                    self.log_callback(
                        "Windows detected - using forceful termination for Java process"
                    )

                # Step 1: Use taskkill with process tree kill (most effective for Java)
                try:
                    if self.log_callback:
                        self.log_callback(f"Using taskkill /F /T /PID {pid}")
                    result = subprocess.run(
                        f"taskkill /F /T /PID {pid}",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10.0,
                    )
                    if result.returncode == 0:
                        if self.log_callback:
                            self.log_callback("Process tree killed with taskkill.")

                        # Brief delay to ensure process is gone
                        time.sleep(1.0)

                        # Verify it's actually dead
                        if not self._check_java_processes_running():
                            self.running = False
                            if self.log_callback:
                                self.log_callback("JAR process confirmed stopped.")
                            return True
                        else:
                            if self.log_callback:
                                self.log_callback(
                                    "Process may still be running, trying alternative method..."
                                )
                    else:
                        if self.log_callback:
                            self.log_callback(
                                f"taskkill by PID failed: {result.stderr}"
                            )
                except Exception as e:
                    if self.log_callback:
                        self.log_callback(f"taskkill by PID failed: {e}")

                # Step 2: Kill all java.exe processes running our specific JAR
                try:
                    jar_name = os.path.basename(self.jar_file)
                    if self.log_callback:
                        self.log_callback(
                            f"Killing all java.exe processes running {jar_name}"
                        )

                    # Use more specific command line matching
                    result = subprocess.run(
                        f'taskkill /F /FI "IMAGENAME eq java.exe" /FI "COMMANDLINE eq *{jar_name}*"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10.0,
                    )

                    # Brief delay
                    time.sleep(1.0)

                    if self.log_callback:
                        if result.returncode == 0:
                            self.log_callback(
                                "Java processes killed by command line filter."
                            )
                        else:
                            self.log_callback(
                                f"Command line filter kill result: {result.stderr}"
                            )

                except Exception as e:
                    if self.log_callback:
                        self.log_callback(f"Command line filter kill failed: {e}")

                # Step 3: Nuclear option - kill ALL java.exe processes (if user has multiple Java apps, this might be aggressive)
                try:
                    if self._check_java_processes_running():
                        if self.log_callback:
                            self.log_callback(
                                "WARNING: Trying nuclear option - killing ALL java.exe processes"
                            )

                        result = subprocess.run(
                            "taskkill /F /IM java.exe",
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=10.0,
                        )
                        time.sleep(1.0)

                        if self.log_callback:
                            if result.returncode == 0:
                                self.log_callback("All java.exe processes killed.")
                            else:
                                self.log_callback(
                                    f"Nuclear kill result: {result.stderr}"
                                )

                except Exception as e:
                    if self.log_callback:
                        self.log_callback(f"Nuclear kill failed: {e}")

            else:
                # Non-Windows systems - use standard approach
                if self.log_callback:
                    self.log_callback("Non-Windows system - using standard termination")

                # Try graceful termination first
                self.process.terminate()
                try:
                    self.process.wait(timeout=5.0)
                    if self.log_callback:
                        self.log_callback("Process terminated gracefully.")
                    self.running = False
                    return True
                except subprocess.TimeoutExpired:
                    if self.log_callback:
                        self.log_callback(
                            "Graceful shutdown timed out, force killing..."
                        )

                    # Force kill
                    self.process.kill()
                    self.process.wait(timeout=5.0)
                    if self.log_callback:
                        self.log_callback("Process force killed.")

            self.running = False

            # Final verification
            if self._check_java_processes_running():
                if self.log_callback:
                    self.log_callback(
                        "⚠️  WARNING: Java processes may still be running! Check Task Manager manually."
                    )
                return False  # Return False to indicate incomplete cleanup

            if self.log_callback:
                self.log_callback("✅ JAR process stopped and verified.")
            return True

        except Exception as e:
            if self.log_callback:
                self.log_callback(f"❌ Error in stop_terminal: {e}")
            self.running = False
            return False

    def is_running(self):
        """Check if the terminal is currently running"""
        if not self.running:
            return False

        # Double-check if process is actually alive
        if self.process:
            if self.process.poll() is not None:
                # Process has terminated
                self.running = False
                return False

        return self.running

    def get_downloading_status(self):
        """Check if a download is in progress"""
        return self.is_downloading

    def set_log_callback(self, callback):
        """Set callback function to receive log output"""
        self.log_callback = callback

    def set_download_progress_callback(self, callback):
        """Set callback function to receive download progress updates"""
        self.download_progress_callback = callback

    def set_download_complete_callback(self, callback):
        """Set callback function to be called when download completes"""
        self.download_complete_callback = callback

    def set_auto_start_complete_callback(self, callback):
        """Set callback function to be called when auto-start completes"""
        self.auto_start_complete_callback = callback

    def _read_output(self):
        """Read output from the process and send to callback"""
        try:
            if self.process and self.process.stdout:
                for line in self.process.stdout:
                    if self.log_callback and line.strip():
                        self.log_callback(line.strip())
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error reading output: {e}")
        finally:
            # Check if process has ended
            if self.process and self.process.poll() is not None:
                self.running = False
                if self.log_callback:
                    self.log_callback("Process ended.")

    def open_logs_folder(self):
        """Open the logs folder in file explorer"""
        if os.path.exists(self.logs_folder):
            self._open_folder(self.logs_folder)
            if self.log_callback:
                self.log_callback(f"Opening logs folder: {self.logs_folder}")
            return True
        else:
            if self.log_callback:
                self.log_callback(f"Logs folder not found: {self.logs_folder}")
            return False

    def open_config_folder(self):
        """Open the config folder in file explorer"""
        if os.path.exists(self.config_folder):
            self._open_folder(self.config_folder)
            if self.log_callback:
                self.log_callback(f"Opening config folder: {self.config_folder}")
            return True
        else:
            if self.log_callback:
                self.log_callback(f"Config folder not found: {self.config_folder}")
            return False

    def _open_folder(self, folder_path):
        """Open a folder in the default file explorer"""
        try:
            if sys.platform.startswith("win"):
                os.startfile(folder_path)
            elif sys.platform.startswith("darwin"):  # macOS
                subprocess.call(["open", folder_path])
            else:  # Linux
                subprocess.call(["xdg-open", folder_path])
            return True
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error opening folder: {e}")
            return False

    def _read_properties_file(self):
        """Read the server region settings from config_0.properties file"""
        if os.path.exists(os.path.join(self.config_folder, "config_0.properties")):
            properties_path = os.path.join(self.config_folder, "config_0.properties")
            try:
                with open(properties_path, "r") as f:
                    lines = f.readlines()
                    for line in lines:
                        line = line.strip()
                        if line.startswith("MDDS_REGION="):
                            self.current_mdds_region = line.split("=")[1]
                        elif line.startswith("FPSS_REGION="):
                            self.current_fpss_region = line.split("=")[1]
                if self.log_callback:
                    self.log_callback(
                        f"Current server settings loaded: MDDS={self.current_mdds_region}, FPSS={self.current_fpss_region}"
                    )
            except Exception as e:
                if self.log_callback:
                    self.log_callback(f"Error reading properties file: {e}")

    def update_server_regions(self, mdds_region, fpss_region):
        """Update the server region settings in config_0.properties file"""
        properties_path = os.path.join(self.config_folder, "config_0.properties")

        # Check if properties file exists
        if not os.path.exists(properties_path):
            if self.log_callback:
                self.log_callback(
                    "Properties file not found. It will be created when ThetaTerminal runs for the first time."
                )
            # Save the values for when the file is created
            self.current_mdds_region = mdds_region
            self.current_fpss_region = fpss_region
            return False

        try:
            # Read existing properties file
            with open(properties_path, "r") as f:
                lines = f.readlines()

            # Update region settings
            updated_lines = []
            for line in lines:
                if line.strip().startswith("MDDS_REGION="):
                    updated_lines.append(f"MDDS_REGION={mdds_region}\n")
                elif line.strip().startswith("FPSS_REGION="):
                    updated_lines.append(f"FPSS_REGION={fpss_region}\n")
                else:
                    updated_lines.append(line)

            # Write updated content back to file
            with open(properties_path, "w") as f:
                f.writelines(updated_lines)

            # Update current values
            self.current_mdds_region = mdds_region
            self.current_fpss_region = fpss_region

            if self.log_callback:
                self.log_callback(
                    f"Server settings updated: MDDS={mdds_region}, FPSS={fpss_region}"
                )
            return True
        except Exception as e:
            if self.log_callback:
                self.log_callback(f"Error updating properties file: {e}")
            return False

    def get_server_regions(self):
        """Get the current server region settings"""
        return {
            "mdds_region": self.current_mdds_region,
            "fpss_region": self.current_fpss_region,
            "mdds_options": self.mdds_regions,
            "fpss_options": self.fpss_regions,
        }
