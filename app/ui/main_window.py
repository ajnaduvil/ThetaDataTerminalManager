import tkinter as tk
from tkinter import ttk
import pyperclip
import os
import threading
import time
from tkinter import messagebox
from . import set_window_icon


class ServerSettingsDialog:
    def __init__(self, parent, terminal_manager):
        # Create a new top-level window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Server Settings")
        self.dialog.transient(parent)
        self.dialog.grab_set()  # Modal dialog

        # Set the icon for the dialog
        set_window_icon(self.dialog)

        # Make dialog appear in center of parent
        self.dialog.geometry("400x250")  # Increased height to accommodate buttons
        self.dialog.resizable(False, False)

        self.terminal_manager = terminal_manager

        # Check if config file exists
        self.config_exists = os.path.exists(
            os.path.join(self.terminal_manager.config_folder, "config_0.properties")
        )

        self.create_widgets()

    def create_widgets(self):
        # Get current server regions
        settings = self.terminal_manager.get_server_regions()

        # Create main frame with padding
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title and info
        ttk.Label(
            main_frame, text="Server Region Settings", font=("", 12, "bold")
        ).pack(anchor=tk.W, pady=(0, 10))

        if not self.config_exists:
            ttk.Label(
                main_frame,
                text="Configuration file not found. Settings cannot be changed.\nRun ThetaTerminal first to create the configuration file.",
                foreground="red",
            ).pack(anchor=tk.W, pady=(0, 10))

        # MDDS Region selection
        mdds_frame = ttk.Frame(main_frame)
        mdds_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(mdds_frame, text="MDDS Region:").pack(side=tk.LEFT)

        self.mdds_var = tk.StringVar(value=settings["mdds_region"])
        mdds_combo = ttk.Combobox(
            mdds_frame,
            textvariable=self.mdds_var,
            values=settings["mdds_options"],
            state="readonly" if self.config_exists else "disabled",
            width=20,
        )
        mdds_combo.pack(side=tk.RIGHT)

        # FPSS Region selection
        fpss_frame = ttk.Frame(main_frame)
        fpss_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(fpss_frame, text="FPSS Region:").pack(side=tk.LEFT)

        self.fpss_var = tk.StringVar(value=settings["fpss_region"])
        fpss_combo = ttk.Combobox(
            fpss_frame,
            textvariable=self.fpss_var,
            values=settings["fpss_options"],
            state="readonly" if self.config_exists else "disabled",
            width=20,
        )
        fpss_combo.pack(side=tk.RIGHT)

        # Warning about non-production servers
        ttk.Label(
            main_frame,
            text="Warning: STAGE and DEV servers are for testing only.\nThey may be unstable and have incomplete data.",
            foreground="red",
        ).pack(anchor=tk.W, pady=(5, 10))

        # Add a separator before buttons
        ttk.Separator(main_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Button frame - ensure it's at the bottom with fixed height
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)

        # Reset button (left side)
        reset_btn = ttk.Button(
            button_frame,
            text="Reset to Production",
            command=self.reset_to_production,
            state=tk.NORMAL if self.config_exists else tk.DISABLED,
        )
        reset_btn.pack(side=tk.LEFT)

        # Cancel button
        cancel_btn = ttk.Button(button_frame, text="Close", command=self.dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Apply button
        apply_btn = ttk.Button(
            button_frame,
            text="Apply",
            command=self.apply_settings,
            state=tk.NORMAL if self.config_exists else tk.DISABLED,
        )
        apply_btn.pack(side=tk.RIGHT)

    def reset_to_production(self):
        """Reset server regions to production defaults"""
        # Set to production server values
        self.mdds_var.set("MDDS_NJ_HOSTS")
        self.fpss_var.set("FPSS_NJ_HOSTS")

        # Apply the settings automatically
        self.apply_settings()

    def apply_settings(self):
        if not self.config_exists:
            messagebox.showinfo(
                "Configuration Missing",
                "Cannot apply settings. Run ThetaTerminal first to create the configuration file.",
                parent=self.dialog,
            )
            return

        mdds_region = self.mdds_var.get()
        fpss_region = self.fpss_var.get()

        success = self.terminal_manager.update_server_regions(mdds_region, fpss_region)

        if success:
            messagebox.showinfo(
                "Settings Applied",
                "Server settings have been updated. The changes will take effect the next time ThetaTerminal starts.",
                parent=self.dialog,
            )
            self.dialog.destroy()
        else:
            messagebox.showerror(
                "Error",
                "Failed to update server settings. Please try again.",
                parent=self.dialog,
            )


class MainWindow:
    def __init__(self, root, terminal_manager):
        self.root = root
        self.terminal_manager = terminal_manager

        # Set a minimum size for the window
        self.root.minsize(600, 400)

        # Configure the main frame with padding
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create the credential frame at the top
        self._create_credential_frame()

        # Create the control frame with start/stop buttons
        self._create_control_frame()

        # Create the log area
        self._create_log_area()

        # Create download progress bar (hidden by default)
        self._create_progress_bar()

        # Set the callbacks
        self.terminal_manager.set_log_callback(self._append_log)
        self.terminal_manager.set_download_progress_callback(self._update_progress)
        self.terminal_manager.set_download_complete_callback(self._download_complete)
        self.terminal_manager.set_auto_start_complete_callback(
            self._auto_start_complete
        )

        # Initialize UI state
        self._update_ui_state()

        # Check if JAR file exists on startup
        self._check_jar_file()

    def _create_credential_frame(self):
        """Create the frame for username and password inputs"""
        cred_frame = ttk.Frame(self.main_frame)
        cred_frame.pack(fill=tk.X, pady=(0, 10))

        # Username
        ttk.Label(cred_frame, text="Username:").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 5)
        )
        self.username_var = tk.StringVar(value=self.terminal_manager.username)
        self.username_entry = ttk.Entry(
            cred_frame, textvariable=self.username_var, width=20
        )
        self.username_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))

        # Password
        ttk.Label(cred_frame, text="Password:").grid(
            row=0, column=2, sticky=tk.W, padx=(10, 5)
        )
        self.password_var = tk.StringVar(value=self.terminal_manager.password)
        self.password_entry = ttk.Entry(
            cred_frame, textvariable=self.password_var, show="*", width=20
        )
        self.password_entry.grid(row=0, column=3, sticky=tk.W)

        # Show/Hide password button
        self.show_password = tk.BooleanVar(value=False)
        self.show_password_btn = ttk.Checkbutton(
            cred_frame,
            text="Show",
            variable=self.show_password,
            command=self._toggle_password_visibility,
        )
        self.show_password_btn.grid(row=0, column=4, sticky=tk.W, padx=(5, 0))

    def _toggle_password_visibility(self):
        """Toggle password visibility"""
        if self.show_password.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")

    def _create_control_frame(self):
        """Create the frame with control buttons"""
        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.pack(fill=tk.X, pady=(0, 10))

        # Start button with icon color
        self.start_btn = ttk.Button(
            self.control_frame,
            text="▶ Start",
            command=self._start_terminal,
            style="Green.TButton",
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Stop button with icon color
        self.stop_btn = ttk.Button(
            self.control_frame,
            text="■ Stop",
            command=self._stop_terminal,
            style="Red.TButton",
        )
        self.stop_btn.pack(side=tk.LEFT)

        # Create a separator
        ttk.Separator(self.control_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=10, fill=tk.Y
        )

        # Folder access buttons
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

        # Server settings button
        ttk.Button(
            self.control_frame,
            text="🌐 Servers",
            command=self._open_server_settings,
        ).pack(side=tk.LEFT)

        # Define styles for colored buttons
        self.root.tk_setPalette(background="#f0f0f0")

        style = ttk.Style()
        style.configure("Green.TButton", foreground="green")
        style.configure("Red.TButton", foreground="red")

    def _create_progress_bar(self):
        """Create the download progress frame (initially hidden)"""
        self.progress_frame = ttk.Frame(self.main_frame)
        self.progress_frame.pack(fill=tk.X, pady=(0, 10))
        self.progress_frame.pack_forget()  # Hide initially

        # Progress label
        self.progress_label = ttk.Label(
            self.progress_frame, text="Downloading ThetaTerminal.jar: 0%"
        )
        self.progress_label.pack(anchor=tk.W, pady=(0, 5))

        # Progress bar
        self.progress_bar = ttk.Progressbar(
            self.progress_frame, orient=tk.HORIZONTAL, length=100, mode="determinate"
        )
        self.progress_bar.pack(fill=tk.X)

    def _create_log_area(self):
        """Create the log text area with controls"""
        log_frame = ttk.Frame(self.main_frame)
        log_frame.pack(fill=tk.BOTH, expand=True)

        # Log area label
        ttk.Label(log_frame, text="Log Output:").pack(anchor=tk.W)

        # Create a frame for the text widget and scrollbar
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        # Log text area with scrollbar
        self.log_text = tk.Text(text_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)

        # Create log control buttons
        log_controls = ttk.Frame(log_frame)
        log_controls.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(log_controls, text="Clear Log", command=self._clear_log).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(log_controls, text="Copy to Clipboard", command=self._copy_log).pack(
            side=tk.LEFT
        )

    def _check_jar_file(self):
        """Check if JAR file exists on startup"""
        if not os.path.exists(self.terminal_manager.jar_file):
            self._append_log(f"{self.terminal_manager.jar_file} not found.")
            reply = messagebox.askyesno(
                "File Missing",
                f"{self.terminal_manager.jar_file} is not found. Do you want to download it now?",
                parent=self.root,
            )
            if reply:
                self._append_log("Starting download...")
                self._update_ui_state_for_download(True)
                self.terminal_manager._download_jar_file_async()
                self.progress_frame.pack(
                    fill=tk.X, pady=(0, 10), after=self.control_frame
                )
            else:
                self._append_log(
                    "Download cancelled. You'll need the JAR file to start the terminal."
                )

    def _download_complete(self):
        """Handle the download completion"""

        # Use a separate thread to update UI state to avoid threading issues
        def enable_ui():
            time.sleep(0.5)  # Small delay to ensure all UI updates are processed
            self._update_ui_state_for_download(False)
            self._append_log("ThetaTerminal.jar is now ready to use.")

            # Explicitly enable all input fields
            self.root.after(100, self._force_enable_inputs)

        threading.Thread(target=enable_ui, daemon=True).start()

    def _force_enable_inputs(self):
        """Force enable all input fields"""
        self.username_entry.config(state=tk.NORMAL)
        self.password_entry.config(state=tk.NORMAL)
        self.show_password_btn.config(state=tk.NORMAL)
        if not self.terminal_manager.is_running():
            self.start_btn.config(state=tk.NORMAL)
        self.root.update_idletasks()

    def _update_ui_state_for_download(self, is_downloading):
        """Update UI elements based on download state"""
        state = tk.DISABLED if is_downloading else tk.NORMAL

        # Update the input fields and buttons
        self.username_entry.config(state=state)
        self.password_entry.config(state=state)
        self.show_password_btn.config(state=state)

        # Only enable start button if not downloading and not running
        if not is_downloading and not self.terminal_manager.is_running():
            self.start_btn.config(state=tk.NORMAL)
        else:
            self.start_btn.config(state=tk.DISABLED)

        # Force update
        self.root.update_idletasks()

    def _update_progress(self, percentage, downloaded, total_size):
        """Update the progress bar and label"""
        # Handle download completion
        if percentage >= 100:
            if self.progress_frame.winfo_ismapped():
                self.progress_frame.pack_forget()
                self._append_log("Download complete.")
            return

        # Show progress frame if not visible
        if not self.progress_frame.winfo_ismapped():
            self.progress_frame.pack(fill=tk.X, pady=(0, 10), after=self.control_frame)

        # Format the label with progress information
        if total_size > 0:
            downloaded_mb = downloaded / (1024 * 1024)
            total_mb = total_size / (1024 * 1024)
            self.progress_label.config(
                text=f"Downloading ThetaTerminal.jar: {percentage}% ({downloaded_mb:.1f} MB / {total_mb:.1f} MB)"
            )
        else:
            self.progress_label.config(
                text=f"Downloading ThetaTerminal.jar: {percentage}%"
            )

        # Update the progress bar
        self.progress_bar["value"] = percentage

        # Ensure the update is displayed immediately
        self.root.update_idletasks()

    def _start_terminal(self):
        """Start the terminal with the given credentials"""
        username = self.username_var.get()
        password = self.password_var.get()

        if not username or not password:
            self._append_log("Error: Username and password are required")
            return

        success = self.terminal_manager.start_terminal(username, password)
        if success:
            self._update_ui_state()
        elif self.terminal_manager.get_downloading_status():
            self._update_ui_state_for_download(True)

    def _stop_terminal(self):
        """Stop the terminal if it's running"""
        if not self.terminal_manager.is_running():
            return

        # Immediately update UI to show stopping state
        self.stop_btn.config(state=tk.DISABLED, text="■ Stopping...")
        self.start_btn.config(state=tk.DISABLED)
        self._append_log("Stopping terminal...")

        # Force UI update
        self.root.update_idletasks()

        # Set up a timeout to force UI update even if stop operation hangs
        # Our simplified stop method has a 5s timeout, so give it a bit extra
        timeout_timer = threading.Timer(7.0, self._force_stop_complete)
        timeout_timer.daemon = True
        timeout_timer.start()

        # Run stop operation in background thread to avoid blocking UI
        def stop_in_background():
            try:
                success = self.terminal_manager.stop_terminal()
                # Cancel the timeout timer since we completed normally
                timeout_timer.cancel()
                # Schedule UI update on main thread
                self.root.after(0, lambda: self._on_stop_complete(success))
            except Exception as e:
                # Cancel the timeout timer
                timeout_timer.cancel()
                # Schedule error handling on main thread
                self.root.after(0, lambda: self._on_stop_error(str(e)))

        stop_thread = threading.Thread(target=stop_in_background, daemon=True)
        stop_thread.start()

    def _force_stop_complete(self):
        """Force complete the stop operation if it takes too long"""
        self._append_log("Stop operation timed out - forcing completion...")
        self.root.after(0, lambda: self._on_stop_complete(False))

    def _on_stop_complete(self, success):
        """Handle stop operation completion on main UI thread"""
        if success:
            self._append_log("Terminal stopped successfully.")
        else:
            self._append_log(
                "Warning: Terminal stop operation may not have completed successfully."
            )

        # Reset button states
        self.stop_btn.config(text="■ Stop")
        self._update_ui_state()

    def _on_stop_error(self, error_msg):
        """Handle stop operation error on main UI thread"""
        self._append_log(f"Error stopping terminal: {error_msg}")

        # Reset button states
        self.stop_btn.config(text="■ Stop")
        self._update_ui_state()

    def _update_ui_state(self):
        """Update UI elements based on the terminal state"""
        running = self.terminal_manager.is_running()
        downloading = self.terminal_manager.get_downloading_status()

        # If downloading, use download-specific UI state
        if downloading:
            self._update_ui_state_for_download(True)
            return

        # Update button states
        if running:
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)

            # Disable input fields while running
            self.username_entry.config(state=tk.DISABLED)
            self.password_entry.config(state=tk.DISABLED)
            self.show_password_btn.config(state=tk.DISABLED)
        else:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

            # Enable input fields when not running
            self.username_entry.config(state=tk.NORMAL)
            self.password_entry.config(state=tk.NORMAL)
            self.show_password_btn.config(state=tk.NORMAL)

        # Force update
        self.root.update_idletasks()

    def _append_log(self, message):
        """Append a message to the log text area"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)  # Scroll to the end
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        """Clear the log text area"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _copy_log(self):
        """Copy log contents to clipboard"""
        log_content = self.log_text.get(1.0, tk.END)
        pyperclip.copy(log_content)
        self._append_log("Log copied to clipboard")

    def _open_logs_folder(self):
        """Open the logs folder in file explorer"""
        success = self.terminal_manager.open_logs_folder()
        if not success:
            messagebox.showerror(
                "Folder Not Found",
                f"Logs folder not found at: {self.terminal_manager.logs_folder}",
                parent=self.root,
            )

    def _open_config_folder(self):
        """Open the config folder in file explorer"""
        success = self.terminal_manager.open_config_folder()
        if not success:
            messagebox.showerror(
                "Folder Not Found",
                f"Config folder not found at: {self.terminal_manager.config_folder}",
                parent=self.root,
            )

    def _open_server_settings(self):
        """Open the server settings dialog"""
        ServerSettingsDialog(self.root, self.terminal_manager)

    def _auto_start_complete(self, success):
        """Handle the auto-start completion"""

        # Schedule UI update on the main thread
        def update_ui():
            if success:
                self._append_log("Auto-start completed successfully.")
            else:
                self._append_log("Auto-start failed.")
            self._update_ui_state()

        self.root.after(0, update_ui)
