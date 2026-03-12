import tkinter as tk
from tkinter import messagebox
import threading
import sys
from app.terminal_manager import TERMINAL_PROFILES, TerminalManager
from app.ui.main_window import MainWindow
from app.ui import set_window_icon


def main():
    root = tk.Tk()
    root.title("ThetaData Terminal Manager")

    # Set the window icon
    if set_window_icon(root):
        print("Window icon set successfully")
    else:
        print("Could not set window icon")

    # Create terminal managers for both supported terminal versions
    terminal_managers = {
        key: TerminalManager(profile)
        for key, profile in TERMINAL_PROFILES.items()
    }

    # Create the main window
    main_window = MainWindow(root, terminal_managers)

    # Set up proper exit handling
    def on_closing():
        running_managers = [
            manager
            for manager in terminal_managers.values()
            if manager.is_running()
        ]

        if running_managers:
            if messagebox.askyesno(
                "Confirm Exit",
                (
                    "One or more terminals are still running. "
                    "Do you want to stop them and exit?"
                ),
                parent=root,
            ):
                # Disable window interactions and show status
                root.config(cursor="wait")
                root.title("ThetaData Terminal Manager - Stopping...")

                # Update UI immediately
                root.update_idletasks()

                # Stop terminal in background - simplified approach
                def stop_and_exit():
                    try:
                        for manager in running_managers:
                            stop_success = manager.stop_terminal()
                            if not stop_success:
                                print(
                                    f"Warning: {manager.profile.display_name} may not have stopped cleanly"
                                )
                            manager.cleanup()

                    except Exception as e:
                        print(f"Error during shutdown: {e}")

                    finally:
                        # Schedule window destruction on main thread
                        root.after(0, force_exit)

                def force_exit():
                    # Additional cleanup for Windows to help release file handles
                    if sys.platform.startswith("win"):
                        # Explicitly call garbage collection
                        import gc

                        gc.collect()

                    root.destroy()

                # Start background stop operation
                exit_thread = threading.Thread(target=stop_and_exit, daemon=True)
                exit_thread.start()

                # Don't return here - let the background thread handle exit
                return
        else:
            # Additional cleanup for Windows to help release file handles
            if sys.platform.startswith("win"):
                # Explicitly call garbage collection
                import gc

                gc.collect()

            root.destroy()

    # Bind closing event
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Start the UI loop
    root.mainloop()


if __name__ == "__main__":
    main()
