#!/usr/bin/env python3
"""
Package Release Script for ThetaData Terminal Manager

This script builds the application and packages it as a zip file for GitHub releases.
The zip file includes the version name in both the folder and file names.
"""

import os
import subprocess
import shutil
import sys
import zipfile
import platform
from datetime import datetime
from pathlib import Path
from version_info import (
    get_semantic_version,
    VERSION_MAJOR,
    VERSION_MINOR,
    VERSION_PATCH,
)
from build import build_executable


def clean_release_artifacts():
    """Clean up any existing release artifacts"""
    print("Cleaning up previous release artifacts...")

    # Create releases directory if it doesn't exist
    releases_dir = "releases"
    if not os.path.exists(releases_dir):
        os.makedirs(releases_dir)
        print(f"Created releases directory: {releases_dir}")

    # Clean up any release artifacts in the root directory (legacy)
    for item in os.listdir("."):
        if item.startswith("ThetaDataTerminalManager-v") and os.path.isdir(item):
            print(f"Removing legacy release folder: {item}")
            shutil.rmtree(item)
        elif item.startswith("ThetaDataTerminalManager-v") and item.endswith(".zip"):
            print(f"Removing legacy release zip: {item}")
            os.remove(item)
        elif item.startswith("release_info_v") and item.endswith(".txt"):
            print(f"Removing legacy release info: {item}")
            os.remove(item)


def create_release_folder(version):
    """Create a release folder with version-specific name in releases directory"""
    releases_dir = "releases"
    folder_name = f"ThetaDataTerminalManager-v{version}"
    full_path = os.path.join(releases_dir, folder_name)

    if os.path.exists(full_path):
        shutil.rmtree(full_path)

    os.makedirs(full_path)
    print(f"Created release folder: {full_path}")
    return full_path


def copy_release_files(release_folder):
    """Copy necessary files to the release folder"""
    print("Copying release files...")

    # Determine executable name based on platform
    is_windows = sys.platform.startswith("win")
    exe_name = (
        "ThetaDataTerminalManager.exe" if is_windows else "ThetaDataTerminalManager"
    )
    exe_path = os.path.join("dist", exe_name)

    if not os.path.exists(exe_path):
        raise FileNotFoundError(
            f"Executable not found at {exe_path}. Please build first."
        )

    # Copy executable
    shutil.copy2(exe_path, release_folder)
    print(f"Copied executable: {exe_name}")

    # Copy README
    if os.path.exists("README.md"):
        shutil.copy2("README.md", release_folder)
        print("Copied README.md")

    # Create a simple release notes file
    version = get_semantic_version()
    release_notes_content = f"""# ThetaData Terminal Manager v{version}

## Release Information
- Version: {version}
- Build Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Platform: {platform.system()} {platform.release()}

## Installation
1. Extract this zip file to your desired location
2. Run ThetaDataTerminalManager{'.exe' if is_windows else ''}

## What's New
- Please check the GitHub repository for detailed release notes and changelog

## Support
For issues and support, please visit: https://github.com/ajnaduvil/ThetaDataTerminalManager

---
Built with PyInstaller {datetime.now().year}
"""

    release_notes_path = os.path.join(release_folder, "RELEASE_NOTES.txt")
    with open(release_notes_path, "w", encoding="utf-8") as f:
        f.write(release_notes_content)
    print("Created RELEASE_NOTES.txt")

    # Copy license if it exists
    for license_file in ["LICENSE", "LICENSE.txt", "LICENSE.md"]:
        if os.path.exists(license_file):
            shutil.copy2(license_file, release_folder)
            print(f"Copied {license_file}")
            break


def create_zip_package(release_folder, version):
    """Create a zip package of the release folder"""
    # Extract just the folder name for the zip
    folder_name = os.path.basename(release_folder)
    releases_dir = os.path.dirname(release_folder)
    zip_name = os.path.join(releases_dir, f"{folder_name}.zip")

    print(f"Creating zip package: {zip_name}")

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for root, dirs, files in os.walk(release_folder):
            for file in files:
                file_path = os.path.join(root, file)
                # Create archive path relative to the releases directory
                archive_path = os.path.relpath(file_path, "releases")
                zipf.write(file_path, archive_path)
                print(f"  Added: {archive_path}")

    # Get zip file size
    zip_size = os.path.getsize(zip_name)
    zip_size_mb = zip_size / (1024 * 1024)

    print(f"Zip package created successfully!")
    print(f"File: {zip_name}")
    print(f"Size: {zip_size_mb:.2f} MB")

    return zip_name


def generate_release_info(zip_name, version):
    """Generate release information for GitHub"""
    zip_size = os.path.getsize(zip_name)
    zip_size_mb = zip_size / (1024 * 1024)

    release_info = f"""
# Release Package Information

## Package Details
- **File**: `{zip_name}`
- **Version**: `v{version}`
- **Size**: `{zip_size_mb:.2f} MB`
- **Build Date**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
- **Platform**: `{platform.system()} {platform.release()}`

## GitHub Release Instructions
1. Go to your GitHub repository
2. Click on "Releases" → "Create a new release"
3. Tag version: `v{version}`
4. Release title: `ThetaData Terminal Manager v{version}`
5. Upload the zip file: `{zip_name}`
6. Add release notes describing what's new in this version

## Contents
- ThetaDataTerminalManager executable
- README.md
- RELEASE_NOTES.txt
- License file (if available)

## Installation for Users
1. Download the zip file from the GitHub release
2. Extract to desired location
3. Run the executable

---
Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    info_file = os.path.join("releases", f"release_info_v{version}.txt")
    with open(info_file, "w", encoding="utf-8") as f:
        f.write(release_info)

    print(f"\nRelease information saved to: {info_file}")
    return info_file


def main():
    """Main packaging function"""
    print("=" * 60)
    print("ThetaData Terminal Manager - Release Packaging Script")
    print("=" * 60)

    try:
        # Get version information
        version = get_semantic_version()
        print(f"Packaging version: v{version} (Semantic Versioning)")

        # Clean up previous artifacts
        clean_release_artifacts()

        # Build the executable
        print("\nStep 1: Building executable...")
        if not build_executable():
            print("❌ Build failed! Cannot proceed with packaging.")
            return False

        print("✅ Build completed successfully!")

        # Create release folder
        print("\nStep 2: Creating release folder...")
        release_folder = create_release_folder(version)

        # Copy files to release folder
        print("\nStep 3: Copying release files...")
        copy_release_files(release_folder)

        # Create zip package
        print("\nStep 4: Creating zip package...")
        zip_name = create_zip_package(release_folder, version)

        # Generate release information
        print("\nStep 5: Generating release information...")
        info_file = generate_release_info(zip_name, version)

        print("\n" + "=" * 60)
        print("✅ PACKAGING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"📦 Release package: {zip_name}")
        print(f"📋 Release info: {info_file}")
        print(f"📁 Release folder: {release_folder}")
        print("\nYour release is ready for GitHub!")
        print("Check the release_info file for upload instructions.")

        return True

    except Exception as e:
        print(f"\n❌ Error during packaging: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
