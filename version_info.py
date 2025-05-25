# Version file for PyInstaller
# This file defines the metadata that will be embedded in the executable

import os

# Version information - update these as needed
VERSION_MAJOR = 1
VERSION_MINOR = 0
VERSION_PATCH = 0
VERSION_BUILD = 0

# Construct version strings
VERSION_STRING = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}.{VERSION_BUILD}"
VERSION_TUPLE = (VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH, VERSION_BUILD)

# File information
COMPANY_NAME = ""
FILE_DESCRIPTION = "ThetaData Terminal Manager - GUI for managing ThetaTerminal.jar"
FILE_VERSION = VERSION_STRING
INTERNAL_NAME = "ThetaDataTerminalManager"
ORIGINAL_FILENAME = "ThetaDataTerminalManager.exe"
PRODUCT_NAME = "ThetaData Terminal Manager"
PRODUCT_VERSION = VERSION_STRING
AUTHOR = "ajnaduvil"

# Generate the version info structure for PyInstaller
version_info = f"""
# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers={VERSION_TUPLE},
    prodvers={VERSION_TUPLE},
    # Contains a bitmask that specifies the valid bits 'flags'r
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{COMPANY_NAME}'),
        StringStruct(u'Author', u'{AUTHOR}'),
        StringStruct(u'FileDescription', u'{FILE_DESCRIPTION}'),
        StringStruct(u'FileVersion', u'{FILE_VERSION}'),
        StringStruct(u'InternalName', u'{INTERNAL_NAME}'),
        StringStruct(u'OriginalFilename', u'{ORIGINAL_FILENAME}'),
        StringStruct(u'ProductName', u'{PRODUCT_NAME}'),
        StringStruct(u'ProductVersion', u'{PRODUCT_VERSION}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""


def get_version_string():
    """Get the version string"""
    return VERSION_STRING


def get_version_info_content():
    """Get the formatted version info content for PyInstaller"""
    return version_info


def write_version_file(filepath="version_info.txt"):
    """Write the version info to a file for PyInstaller"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(version_info)
    return filepath


if __name__ == "__main__":
    # Generate the version file when run directly
    version_file = write_version_file()
    print(f"Version file created: {version_file}")
    print(f"Version: {VERSION_STRING}")
