import os
import subprocess
import shutil
import sys
import platform
from version_info import write_version_file, get_version_string


def build_executable():
    """Build the executable using PyInstaller"""
    print("Building ThetaData Terminal Manager executable...")

    # Get version information
    version = get_version_string()
    print(f"Version: {version}")

    # Clean up previous build artifacts if they exist
    if os.path.exists("dist"):
        print("Cleaning up previous build files...")
        shutil.rmtree("dist")
    if os.path.exists("build"):
        shutil.rmtree("build")
    for file in os.listdir("."):
        if file.endswith(".spec"):
            os.remove(file)

    # Generate version file for PyInstaller
    version_file = write_version_file("version_info.txt")
    print(f"Generated version file: {version_file}")

    # Create directory for icon if it doesn't exist
    icon_dir = os.path.join("app", "resources")
    if not os.path.exists(icon_dir):
        os.makedirs(icon_dir)

    # Determine if we're on Windows
    is_windows = sys.platform.startswith("win")

    # Check for icon file
    icon_paths = [
        os.path.join(icon_dir, "icon.ico"),
        os.path.join(icon_dir, "icon_32x32.ico"),
        os.path.join(icon_dir, "icon_128x128.ico"),
    ]

    icon_param = ""
    for icon_path in icon_paths:
        if os.path.exists(icon_path):
            print(f"Found icon file: {icon_path} ({os.path.getsize(icon_path)} bytes)")
            icon_param = f"--icon={icon_path}"
            break

    if not icon_param:
        print(f"No icon file found. Searched in:")
        for path in icon_paths:
            print(f"  - {path}")
        print("The executable will use the default Python icon.")
        print("To add a custom icon, place icon.ico in app/resources/")
    else:
        print(f"Using icon: {icon_param}")

    # Data separator for PyInstaller is different on Windows vs. other platforms
    separator = ";" if is_windows else ":"

    # Build the PyInstaller command
    cmd = [
        "uv",
        "run",
        "pyinstaller",
        "--name=ThetaDataTerminalManager",
        "--onefile",
        "--windowed",
        f"--version-file={version_file}",  # Add version file
    ]

    # Add icon resources as data files so they're available to the running app
    if os.path.exists(icon_dir):
        cmd.append(f"--add-data={icon_dir}{separator}app/resources")
        print(f"Adding icon resources from {icon_dir}")

    # Add icon if available
    if icon_param:
        cmd.append(icon_param)

    # Add main script
    cmd.append("main.py")

    # Execute the command
    print(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Error building executable:")
        print(result.stderr)
        if "icon" in result.stderr.lower():
            print("\nIcon-related error detected. Trying without icon...")
            # Remove icon parameter and try again
            cmd_no_icon = [c for c in cmd if not c.startswith("--icon")]
            result = subprocess.run(cmd_no_icon, capture_output=True, text=True)
            if result.returncode == 0:
                print("Build successful without icon!")
            else:
                print("Build failed even without icon:")
                print(result.stderr)
                return False
        else:
            # Try with spec file if direct command fails
            print("Attempting to build with spec file...")
            if os.path.exists("ThetaDataTerminalManager.spec"):
                spec_result = subprocess.run(
                    ["uv", "run", "pyinstaller", "ThetaDataTerminalManager.spec"],
                    capture_output=True,
                    text=True,
                )
                if spec_result.returncode != 0:
                    print("Error building with spec file:")
                    print(spec_result.stderr)
                    return False
                else:
                    print("Build with spec file completed successfully!")
            else:
                return False

    # Check if executable was created
    exe_path = os.path.join(
        "dist",
        "ThetaDataTerminalManager.exe" if is_windows else "ThetaDataTerminalManager",
    )
    if os.path.exists(exe_path):
        print("Build completed successfully!")
        print(f"Executable created at: {os.path.abspath(exe_path)}")
        print(f"Version: {version}")

        # Clean up version file
        if os.path.exists(version_file):
            os.remove(version_file)
            print("Cleaned up temporary version file")

        return True
    else:
        print(f"Build process completed, but executable not found at {exe_path}")
        return False


if __name__ == "__main__":
    build_executable()
