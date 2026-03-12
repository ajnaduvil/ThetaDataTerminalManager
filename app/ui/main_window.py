import os
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import pyperclip

from . import set_window_icon


class ServerSettingsDialog:
    def __init__(self, parent, terminal_manager):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Server Settings")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        set_window_icon(self.dialog)

        self.dialog.geometry("400x250")
        self.dialog.resizable(False, False)

        self.terminal_manager = terminal_manager
        self.config_exists = os.path.exists(
            os.path.join(self.terminal_manager.config_folder, "config_0.properties")
        )

        self.create_widgets()

    def create_widgets(self):
        settings = self.terminal_manager.get_server_regions()

        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame, text="Server Region Settings", font=("", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))

        if not self.config_exists:
            ttk.Label(
                main_frame,
                text=(
                    "Configuration file not found. Settings cannot be changed.\n"
                    "Run ThetaTerminal v2 first to create the configuration file."
                ),
                foreground="red",
            ).pack(anchor=tk.W, pady=(0, 10))

        mdds_frame = ttk.Frame(main_frame)
        mdds_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(mdds_frame, text="MDDS Region:").pack(side=tk.LEFT)

        self.mdds_var = tk.StringVar(value=settings["mdds_region"])
        ttk.Combobox(
            mdds_frame,
            textvariable=self.mdds_var,
            values=settings["mdds_options"],
            state="readonly" if self.config_exists else "disabled",
            width=20,
        ).pack(side=tk.RIGHT)

        fpss_frame = ttk.Frame(main_frame)
        fpss_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(fpss_frame, text="FPSS Region:").pack(side=tk.LEFT)

        self.fpss_var = tk.StringVar(value=settings["fpss_region"])
        ttk.Combobox(
            fpss_frame,
            textvariable=self.fpss_var,
            values=settings["fpss_options"],
            state="readonly" if self.config_exists else "disabled",
            width=20,
        ).pack(side=tk.RIGHT)

        ttk.Label(
            main_frame,
            text=(
                "Warning: STAGE and DEV servers are for testing only.\n"
                "They may be unstable and have incomplete data."
            ),
            foreground="red",
        ).pack(anchor=tk.W, pady=(5, 10))

        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)

        ttk.Button(
            button_frame,
            text="Reset to Production",
            command=self.reset_to_production,
            state=tk.NORMAL if self.config_exists else tk.DISABLED,
        ).pack(side=tk.LEFT)

        ttk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(
            side=tk.RIGHT, padx=(5, 0)
        )

        ttk.Button(
            button_frame,
            text="Apply",
            command=self.apply_settings,
            state=tk.NORMAL if self.config_exists else tk.DISABLED,
        ).pack(side=tk.RIGHT)

    def reset_to_production(self):
        self.mdds_var.set("MDDS_NJ_HOSTS")
        self.fpss_var.set("FPSS_NJ_HOSTS")
        self.apply_settings()

    def apply_settings(self):
        if not self.config_exists:
            messagebox.showinfo(
                "Configuration Missing",
                "Cannot apply settings. Run ThetaTerminal v2 first to create the configuration file.",
                parent=self.dialog,
            )
            return

        success = self.terminal_manager.update_server_regions(
            self.mdds_var.get(), self.fpss_var.get()
        )

        if success:
            messagebox.showinfo(
                "Settings Applied",
                (
                    "Server settings have been updated. The changes will take effect "
                    "the next time ThetaTerminal v2 starts."
                ),
                parent=self.dialog,
            )
            self.dialog.destroy()
        else:
            messagebox.showerror(
                "Error",
                "Failed to update server settings. Please try again.",
                parent=self.dialog,
            )


class TerminalTab:
    def __init__(self, parent, terminal_manager, start_callback):
        self.parent = parent
        self.terminal_manager = terminal_manager
        self.start_callback = start_callback
        self.frame = ttk.Frame(parent, padding="10")

        self.username_var = tk.StringVar(value=self.terminal_manager.username)
        self.password_var = tk.StringVar(value=self.terminal_manager.password)
        self.show_password = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar()
        self.info_var = tk.StringVar()

        self._create_header()
        self._create_credential_frame()
        self._create_control_frame()
        self._create_progress_bar()
        self._create_log_area()

        self.terminal_manager.set_log_callback(self._append_log)
        self.terminal_manager.set_download_progress_callback(self._update_progress)
        self.terminal_manager.set_download_complete_callback(self._download_complete)
        self.terminal_manager.set_auto_start_complete_callback(
            self._auto_start_complete
        )

        self._set_default_messages()
        self._note_missing_jar()
        self._update_ui_state()

    def _set_default_messages(self):
        self.status_var.set(
            f"{self.terminal_manager.profile.display_name} requires Java "
            f"{self.terminal_manager.profile.java_min_version}+"
        )

        if self.terminal_manager.profile.key == "v3":
            self.info_var.set(
                "v3 uses creds.txt beside ThetaTerminalv3.jar and launches via "
                "java -jar ThetaTerminalv3.jar. You can run it alongside v2."
            )
        else:
            self.info_var.set(
                "v2 launches with username/password CLI arguments and supports "
                "server region configuration. You can run it alongside v3."
            )

    def _note_missing_jar(self):
        if not self.terminal_manager.check_jar_file():
            self._append_log(
                f"{self.terminal_manager.profile.jar_file} is not downloaded yet. "
                "Click Start to download and launch it automatically."
            )

    def _create_header(self):
        header_frame = ttk.Frame(self.frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            header_frame,
            text=self.terminal_manager.profile.display_name,
            font=("", 13, "bold"),
        ).pack(anchor=tk.W)

        ttk.Label(
            header_frame,
            textvariable=self.status_var,
            foreground="#0b5394",
        ).pack(anchor=tk.W, pady=(2, 0))

        ttk.Label(
            header_frame,
            textvariable=self.info_var,
            wraplength=760,
            foreground="#555555",
        ).pack(anchor=tk.W, pady=(2, 0))

    def _create_credential_frame(self):
        cred_frame = ttk.Frame(self.frame)
        cred_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(cred_frame, text="Username / Email:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5)
        )
        self.username_entry = ttk.Entry(
            cred_frame, textvariable=self.username_var, width=24
        )
        self.username_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))

        ttk.Label(cred_frame, text="Password:").grid(
            row=0, column=2, sticky=tk.W, padx=(10, 5)
        )
        self.password_entry = ttk.Entry(
            cred_frame, textvariable=self.password_var, show="*", width=24
        )
        self.password_entry.grid(row=0, column=3, sticky=tk.W)

        self.show_password_btn = ttk.Checkbutton(
            cred_frame,
            text="Show",
            variable=self.show_password,
            command=self._toggle_password_visibility,
        )
        self.show_password_btn.grid(row=0, column=4, sticky=tk.W, padx=(5, 0))

    def _toggle_password_visibility(self):
        self.password_entry.config(show="" if self.show_password.get() else "*")

    def _create_control_frame(self):
        self.control_frame = ttk.Frame(self.frame)
        self.control_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = ttk.Button(
            self.control_frame,
            text="▶ Start",
            command=self._request_start,
            style="Green.TButton",
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.stop_btn = ttk.Button(
            self.control_frame,
            text="■ Stop",
            command=self._stop_terminal,
            style="Red.TButton",
        )
        self.stop_btn.pack(side=tk.LEFT)

        ttk.Separator(self.control_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=10, fill=tk.Y
        )

        ttk.Button(
            self.control_frame,
            text="📁 Logs",
            command=self._open_logs_folder,
        ).pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(
            self.control_frame,
            text="📁 Config",
            command=self._open_config_folder,
        ).pack(side=tk.LEFT, padx=(0, 5))

        if self.terminal_manager.profile.supports_server_settings:
            ttk.Button(
                self.control_frame,
                text="🌐 Servers",
                command=self._open_server_settings,
            ).pack(side=tk.LEFT)
        else:
            ttk.Label(
                self.control_frame,
                text="Server settings are only available for v2",
                foreground="#666666",
            ).pack(side=tk.LEFT)

    def _create_progress_bar(self):
        self.progress_frame = ttk.Frame(self.frame)
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        self.progress_frame.pack_forget()

        self.progress_label = ttk.Label(
            self.progress_frame,
            text=f"Downloading {self.terminal_manager.profile.jar_file}: 0%",
        )
        self.progress_label.pack(anchor=tk.W, pady=(0, 5))

        self.progress_bar = ttk.Progressbar(
            self.progress_frame, orient=tk.HORIZONTAL, length=100, mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X)

    def _create_log_area(self):
        log_frame = ttk.Frame(self.frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(log_frame, text="Log Output:").pack(anchor=tk.W)

        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(text_frame, wrap=tk.WORD, height=15, state=tk.DISABLED)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(text_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        log_controls = ttk.Frame(log_frame)
        log_controls.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(log_controls, text="Clear Log", command=self._clear_log).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(
            log_controls,
            text="Copy to Clipboard",
            command=self._copy_log,
        ).pack(side=tk.LEFT)

    def _request_start(self):
        self.start_callback(self)

    def start_terminal(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            self._append_log("Error: Username/email and password are required.")
            return

        success = self.terminal_manager.start_terminal(username, password)
        if success:
            self._update_ui_state()
        elif self.terminal_manager.get_downloading_status():
            self._update_ui_state_for_download(True)

    def _stop_terminal(self):
        if not self.terminal_manager.is_running():
            return

        self.stop_btn.config(state=tk.DISABLED, text="■ Stopping...")
        self.start_btn.config(state=tk.DISABLED)
        self._append_log("Stopping terminal...")
        self.frame.update_idletasks()

        timeout_timer = threading.Timer(7.0, self._force_stop_complete)
        timeout_timer.daemon = True
        timeout_timer.start()

        def stop_in_background():
            try:
                success = self.terminal_manager.stop_terminal()
                timeout_timer.cancel()
                self.frame.after(0, lambda: self._on_stop_complete(success))
            except Exception as exc:
                timeout_timer.cancel()
                self.frame.after(0, lambda: self._on_stop_error(str(exc)))

        threading.Thread(target=stop_in_background, daemon=True).start()

    def _force_stop_complete(self):
        def complete():
            self._append_log("Stop operation timed out - forcing completion...")
            self._on_stop_complete(False)

        self.frame.after(0, complete)

    def _on_stop_complete(self, success):
        if success:
            self._append_log("Terminal stopped successfully.")
        else:
            self._append_log(
                "Warning: Terminal stop operation may not have completed successfully."
            )

        self.stop_btn.config(text="■ Stop")
        self._update_ui_state()

    def _on_stop_error(self, error_msg):
        self._append_log(f"Error stopping terminal: {error_msg}")
        self.stop_btn.config(text="■ Stop")
        self._update_ui_state()

    def _download_complete(self, success):
        self.frame.after(0, lambda: self._finish_download_ui(success))

    def _finish_download_ui(self, success):
        self._update_ui_state_for_download(False)
        if success:
            self._append_log(
                f"{self.terminal_manager.profile.jar_file} is now ready to use."
            )
        else:
            self._append_log(
                f"Failed to download {self.terminal_manager.profile.jar_file}."
            )

    def _update_ui_state_for_download(self, is_downloading):
        state = tk.DISABLED if is_downloading else tk.NORMAL

        self.username_entry.config(state=state)
        self.password_entry.config(state=state)
        self.show_password_btn.config(state=state)

        if not is_downloading and not self.terminal_manager.is_running():
            self.start_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.DISABLED)

        if is_downloading and not self.progress_frame.winfo_ismapped():
            self.progress_frame.pack(fill=tk.X, pady=(0, 10), after=self.control_frame)
        elif not is_downloading and self.progress_frame.winfo_ismapped():
            self.progress_frame.pack_forget()

        self.frame.update_idletasks()

    def _update_progress(self, percentage, downloaded, total_size):
        self.frame.after(
            0,
            lambda: self._render_progress(percentage, downloaded, total_size),
        )

    def _render_progress(self, percentage, downloaded, total_size):
        if percentage >= 100:
            if self.progress_frame.winfo_ismapped():
                self.progress_frame.pack_forget()
                self._append_log("Download complete.")
            return

        if not self.progress_frame.winfo_ismapped():
            self.progress_frame.pack(fill=tk.X, pady=(0, 10), after=self.control_frame)

        jar_name = self.terminal_manager.profile.jar_file
        if total_size > 0:
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            self.progress_label.config(
                text=(
                    f"Downloading {jar_name}: {percentage}% "
                    f"({downloaded_mb:.1f} MB / {total_mb:.1f} MB)"
                )
            )
        else:
            self.progress_label.config(text=f"Downloading {jar_name}: {percentage}%")

        self.progress_bar["value"] = percentage
        self.frame.update_idletasks()

    def _update_ui_state(self):
        running = self.terminal_manager.is_running()
        downloading = self.terminal_manager.get_downloading_status()

        if downloading:
            self._update_ui_state_for_download(True)
            return

        if running:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.username_entry.config(state=tk.DISABLED)
            self.password_entry.config(state=tk.DISABLED)
            self.show_password_btn.config(state=tk.DISABLED)
            self.status_var.set(
                f"{self.terminal_manager.profile.display_name} is currently running"
            )
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.username_entry.config(state=tk.NORMAL)
            self.password_entry.config(state=tk.NORMAL)
            self.show_password_btn.config(state=tk.NORMAL)
            self.status_var.set(
                f"{self.terminal_manager.profile.display_name} requires Java "
                f"{self.terminal_manager.profile.java_min_version}+"
            )

        self.frame.update_idletasks()

    def is_running(self):
        return self.terminal_manager.is_running()

    def get_tab_title(self):
        status_dot = "🟢" if self.is_running() else "🔴"
        return f"{status_dot} {self.terminal_manager.profile.display_name}"

    def _append_log(self, message):
        self.frame.after(0, lambda: self._append_log_on_main_thread(message))

    def _append_log_on_main_thread(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _copy_log(self):
        pyperclip.copy(self.log_text.get(1.0, tk.END))
        self._append_log("Log copied to clipboard")

    def _open_logs_folder(self):
        success = self.terminal_manager.open_logs_folder()
        if not success:
            messagebox.showerror(
                "Folder Not Found",
                f"Logs folder not found at: {self.terminal_manager.logs_folder}",
                parent=self.frame.winfo_toplevel(),
            )

    def _open_config_folder(self):
        success = self.terminal_manager.open_config_folder()
        if not success:
            messagebox.showerror(
                "Folder Not Found",
                f"Config folder not found at: {self.terminal_manager.config_folder}",
                parent=self.frame.winfo_toplevel(),
            )

    def _open_server_settings(self):
        ServerSettingsDialog(self.frame.winfo_toplevel(), self.terminal_manager)

    def _auto_start_complete(self, success):
        def update_ui():
            if success:
                self._append_log("Auto-start completed successfully.")
            else:
                self._append_log("Auto-start failed.")
            self._update_ui_state()

        self.frame.after(0, update_ui)


class MainWindow:
    def __init__(self, root, terminal_managers):
        self.root = root
        self.terminal_managers = terminal_managers
        self.root.minsize(760, 500)

        self.root.tk_setPalette(background="#f0f0f0")
        style = ttk.Style()
        style.configure("Green.TButton", foreground="green")
        style.configure("Red.TButton", foreground="red")

        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            self.main_frame,
            text="Manage ThetaTerminal v2 and ThetaTerminal v3 from one interface.",
        ).pack(anchor=tk.W, pady=(0, 8))

        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tabs = {}
        for version_key, manager in self.terminal_managers.items():
            tab = TerminalTab(self.notebook, manager, self._start_requested)
            self.tabs[version_key] = tab
            self.notebook.add(tab.frame, text=tab.get_tab_title())

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._select_saved_tab()
        self._schedule_status_refresh()

    def _select_saved_tab(self):
        default_version = self.terminal_managers["v2"].get_selected_version()
        keys = list(self.tabs.keys())
        if default_version in keys:
            self.notebook.select(keys.index(default_version))

    def _on_tab_changed(self, _event=None):
        version_key = self.get_active_version_key()
        if version_key:
            self.terminal_managers[version_key].set_selected_version(version_key)

    def get_active_version_key(self):
        selected_tab_id = self.notebook.select()
        for version_key, tab in self.tabs.items():
            if str(tab.frame) == selected_tab_id:
                return version_key
        return None

    def get_active_tab(self):
        version_key = self.get_active_version_key()
        return self.tabs.get(version_key)

    def _start_requested(self, tab):
        version_key = tab.terminal_manager.profile.key
        self.terminal_managers[version_key].set_selected_version(version_key)

        tab.start_terminal()

    def _schedule_status_refresh(self):
        self._refresh_tab_titles()
        self.root.after(1000, self._schedule_status_refresh)

    def _refresh_tab_titles(self):
        for index, version_key in enumerate(self.tabs.keys()):
            tab = self.tabs[version_key]
            self.notebook.tab(index, text=tab.get_tab_title())
