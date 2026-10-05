@echo off
REM ---------------------------------------------------------------
REM  BMS Drug Machine - let OTHER PCs open the tool from this PC
REM
REM  Run ONCE on the PC that runs start.bat (asks for admin rights):
REM    1) Windows Firewall: allow incoming TCP on PORT
REM    2) URL reservation http://+:PORT/ for everyone, so serve.ps1
REM       (the PowerShell server) can listen for other PCs without admin
REM
REM  Enable-LAN.bat --remove   = undo both
REM
REM  PORT is read from start.bat (set PORT=...).
REM  ASCII only on purpose - Thai text breaks cmd.exe parsing.
REM ---------------------------------------------------------------
setlocal
set "PORT=8797"
for /f "tokens=2 delims==" %%a in ('findstr /b /i /c:"set PORT=" "%~dp0start.bat" 2^>nul') do set "PORT=%%a"
set "RULE=BMS Drug Machine %PORT%"

set "REMOVE="
set "ELEVATED="
for %%a in (%*) do if /i "%%~a"=="--remove" set "REMOVE=--remove"
for %%a in (%*) do if /i "%%~a"=="--elevated" set "ELEVATED=1"

REM High integrity level (SID S-1-16-12288) = running as administrator
whoami /groups | find "S-1-16-12288" >nul 2>nul
if errorlevel 1 goto elevate

echo ============================================================
if defined REMOVE (echo   Removing LAN access for port %PORT%) else (echo   Allowing other PCs to open BMS Drug Machine on port %PORT%)
echo ============================================================
echo.
if defined REMOVE goto remove

echo [1/2] Windows Firewall rule "%RULE%"
netsh advfirewall firewall delete rule name="%RULE%" >nul 2>nul
netsh advfirewall firewall add rule name="%RULE%" dir=in action=allow protocol=TCP localport=%PORT% profile=any
if errorlevel 1 (echo       [ERROR] could not add the firewall rule) else (echo       OK)
echo.

echo [2/2] URL reservation http://+:%PORT%/ for everyone
netsh http delete urlacl url=http://+:%PORT%/ >nul 2>nul
netsh http add urlacl url=http://+:%PORT%/ sddl=D:(A;;GX;;;WD)
if errorlevel 1 (echo       [ERROR] could not add the URL reservation) else (echo       OK)
echo.

echo Done. Close start.bat if it is running and start it again.
echo Its window then shows the address for other PCs, for example:
echo   http://192.168.x.x:%PORT%/index.html
echo.
echo To undo later:  Enable-LAN.bat --remove
goto end

:remove
netsh advfirewall firewall delete rule name="%RULE%"
netsh http delete urlacl url=http://+:%PORT%/
echo.
echo Done. Only this PC can open the tool now (restart start.bat).
goto end

:elevate
if defined ELEVATED goto noadmin
echo Asking for administrator rights...
powershell -NoProfile -Command "try { Start-Process -FilePath '%~f0' -ArgumentList '--elevated %REMOVE%' -Verb RunAs -ErrorAction Stop } catch { exit 1 }"
if errorlevel 1 goto cancelled
exit /b 0

:cancelled
echo.
echo Administrator rights were not granted - nothing was changed.
goto end

:noadmin
echo [ERROR] Still not running as administrator - nothing was changed.
echo Right-click Enable-LAN.bat and choose "Run as administrator".

:end
echo.
pause
