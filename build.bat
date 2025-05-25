@echo off
echo Building ThetaData Terminal Manager...

REM Clear any existing virtual environment variables to avoid conflicts
set VIRTUAL_ENV=
set PIPENV_ACTIVE=

REM Use uv which manages its own virtual environment
uv run python build.py

if %ERRORLEVEL% EQU 0 (
    echo Build successful!
    echo Executable is located in the "dist" folder
) else (
    echo Build failed with error code %ERRORLEVEL%
)
pause 