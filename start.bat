@echo off
REM ---------------------------------------------------------------
REM  BMS Drug Machine - local web server + HOSxP API proxy
REM
REM  Uses Python 3.7+ (serve.py) when it is installed, otherwise the
REM  Windows PowerShell built into Windows 10/11 (serve.ps1).
REM  Nothing needs to be installed.
REM
REM  start.bat --no-browser   = start the server only
REM  Other PCs can open http://<this-PC-IP>:PORT/index.html after
REM  Enable-LAN.bat has been run once on this PC.
REM
REM  ASCII only on purpose - Thai text breaks cmd.exe parsing.
REM ---------------------------------------------------------------
setlocal
set PORT=8797

REM HOST_IP = address used as the MAIN URL that other PCs open.
REM Leave empty to use this PC's own LAN IP automatically (works on any PC
REM you copy this folder to). Set it only if the PC has several networks
REM and the wrong one is picked, for example:  set HOST_IP=192.168.1.20
set HOST_IP=

REM SERVER = auto | python | powershell
REM auto uses Python when installed. Use powershell when this window says
REM "hosxp.net: CANNOT CONNECT" because the hospital proxy needs the Windows
REM login - the PowerShell server sends it, the Python one cannot.
set SERVER=auto

set "PYOPEN=--open"
set "PSOPEN=-Open"
set "PYHOST="
set "PSHOST="
if defined HOST_IP set "PYHOST=--host=%HOST_IP%"
if defined HOST_IP set "PSHOST=-HostIp %HOST_IP%"
if /i "%~1"=="--no-browser" set "PYOPEN="
if /i "%~1"=="--no-browser" set "PSOPEN="

REM pushd (not cd) also works when the folder is on a network share
pushd "%~dp0" 2>nul || goto nodir
if not exist "index.html" goto nofiles

echo ============================================================
echo   BMS Drug Machine - gateway check dashboard (HOSxP)
echo ------------------------------------------------------------
echo   MAIN URL = this PC's IP address, printed below.
echo   Other PCs open that MAIN URL in their browser.
echo   Keep THIS window OPEN while using the tool.
echo   Close this window (or press Ctrl+C) to stop the server.
echo ------------------------------------------------------------
echo   Do NOT open index.html with a double click (file://).
echo   The HOSxP tunnel rejects file:// requests - use the URL above.
echo ============================================================
echo.

REM Other PCs need the firewall rule made by Enable-LAN.bat (once per PC)
netsh advfirewall firewall show rule name="BMS Drug Machine %PORT%" >nul 2>nul
if errorlevel 1 (
  echo   [NOTE] Other PCs cannot connect yet: the firewall rule is missing.
  echo          Run Enable-LAN.bat once on this PC - it asks for admin rights.
  echo.
)

if /i "%SERVER%"=="powershell" goto usepowershell

REM Is there a real Python 3.7+? The Microsoft Store "python" shortcut fails this test.
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 7) else 1)" >nul 2>nul && set "PY=py -3"
if not defined PY python -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3, 7) else 1)" >nul 2>nul && set "PY=python"
if defined PY if exist "serve.py" goto usepython
goto usepowershell

:usepython
echo   Server: Python
echo.
%PY% serve.py %PORT% %PYOPEN% %PYHOST%
goto stopped

:usepowershell
if not exist "serve.ps1" goto nofiles
where powershell >nul 2>nul || goto nopowershell
echo   Server: Windows PowerShell (Python is not installed - that is OK)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "serve.ps1" -Port %PORT% %PSOPEN% %PSHOST%
goto stopped

:stopped
echo.
echo Server stopped. If it did not start, read the message above:
echo   - port in use       : this tool is already running in another window,
echo                         close that window or change PORT at the top of this file.
echo   - execution policy  : PowerShell scripts are blocked on this PC -
echo                         ask IT to allow them, or install Python 3.
goto end

:nofiles
echo [ERROR] Program files are missing in this folder:
echo   %CD%
echo.
echo Need index.html together with serve.ps1 (or serve.py).
echo If you opened start.bat from inside a ZIP file, right-click the ZIP,
echo choose "Extract All", then run start.bat from the extracted folder.
goto end

:nopowershell
echo [ERROR] Neither Python 3.7+ nor Windows PowerShell was found on this PC.
echo Install Python 3 from https://www.python.org and run this file again.
goto end

:nodir
echo [ERROR] Cannot open the folder of this file:
echo   %~dp0

:end
popd 2>nul
echo.
pause
