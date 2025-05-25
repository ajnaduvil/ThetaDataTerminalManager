#!/usr/bin/env python3
"""
Utility script to update version numbers across all project files
"""
import re
import sys
from pathlib import Path


def update_version_info(major, minor, patch, build=0):
    """Update version_info.py with new version numbers"""
    version_file = Path("version_info.py")
    content = version_file.read_text(encoding="utf-8")

    # Update version components
    content = re.sub(r"VERSION_MAJOR = \d+", f"VERSION_MAJOR = {major}", content)
    content = re.sub(r"VERSION_MINOR = \d+", f"VERSION_MINOR = {minor}", content)
    content = re.sub(r"VERSION_PATCH = \d+", f"VERSION_PATCH = {patch}", content)
    content = re.sub(r"VERSION_BUILD = \d+", f"VERSION_BUILD = {build}", content)

    version_file.write_text(content, encoding="utf-8")
    print(f"Updated {version_file}")


def update_pyproject_toml(major, minor, patch, build=0):
    """Update pyproject.toml with new version"""
    pyproject_file = Path("pyproject.toml")
    content = pyproject_file.read_text(encoding="utf-8")

    version_string = f"{major}.{minor}.{patch}.{build}"
    content = re.sub(r'version = "[^"]*"', f'version = "{version_string}"', content)

    pyproject_file.write_text(content, encoding="utf-8")
    print(f"Updated {pyproject_file}")


def main():
    """Main function to update version numbers"""
    if len(sys.argv) < 4:
        print("Usage: python update_version.py <major> <minor> <patch> [build]")
        print("Example: python update_version.py 1 0 1")
        print("Example: python update_version.py 1 2 0 5")
        sys.exit(1)

    try:
        major = int(sys.argv[1])
        minor = int(sys.argv[2])
        patch = int(sys.argv[3])
        build = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    except ValueError:
        print("Error: Version numbers must be integers")
        sys.exit(1)

    version_string = f"{major}.{minor}.{patch}.{build}"

    print(f"Updating version to: {version_string}")
    print("-" * 40)

    # Update files
    update_version_info(major, minor, patch, build)
    update_pyproject_toml(major, minor, patch, build)

    print("-" * 40)
    print(f"Version updated to {version_string}")
    print("Files updated:")
    print("  - version_info.py")
    print("  - pyproject.toml")
    print("")
    print("Next steps:")
    print("  1. Review the changes")
    print("  2. Build the executable: uv run python build.py")
    print("  3. Test the application")


if __name__ == "__main__":
    main()
