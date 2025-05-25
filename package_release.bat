@echo off
REM Package Release Script for ThetaData Terminal Manager
REM This batch file runs the Python packaging script

echo ============================================================
echo ThetaData Terminal Manager - Release Packaging
echo ============================================================
echo.

REM Check if Python is available via uv
where uv >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: uv is not installed or not in PATH
    echo Please install uv first: https://docs.astral.sh/uv/
    pause
    exit /b 1
)

REM Run the packaging script
echo Running packaging script...
echo.
uv run python package_release.py

REM Check if the script was successful
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo Packaging completed successfully!
    echo ============================================================
    echo.
    echo Your release package is ready for GitHub upload.
    echo Check the generated files in the current directory.
    echo.
) else (
    echo.
    echo ============================================================
    echo Packaging failed!
    echo ============================================================
    echo.
    echo Please check the error messages above.
    echo.
)

pause 