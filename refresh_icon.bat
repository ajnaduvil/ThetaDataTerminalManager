@echo off
echo Refreshing Windows icon cache...

REM Delete icon cache files
attrib -h -s -r "%userprofile%\AppData\Local\IconCache.db"
del /f "%userprofile%\AppData\Local\IconCache.db"

REM For Windows 10/11, also delete the new cache files
if exist "%userprofile%\AppData\Local\Microsoft\Windows\Explorer\iconcache_*.db" (
    attrib -h -s -r "%userprofile%\AppData\Local\Microsoft\Windows\Explorer\iconcache_*.db"
    del /f "%userprofile%\AppData\Local\Microsoft\Windows\Explorer\iconcache_*.db"
)

echo Icon cache cleared. Restarting Windows Explorer...

REM Restart Windows Explorer
taskkill /f /im explorer.exe
start explorer.exe

echo Icon cache refresh complete!
echo If the icon still doesn't appear, try:
echo 1. Right-click the executable and check Properties
echo 2. Rebuild the executable: build.bat
echo 3. Check that icon.ico is a valid Windows icon file
echo 4. The executable is now named: ThetaDataTerminalManager.exe
pause 