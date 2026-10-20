@echo off
rem phonechatXI bridge for Windows. /pchat start in game runs this; you can also double-click it.
title phonechatXI bridge
cd /d "%~dp0"
rem Prefer the py launcher: a bare "python" can be the Microsoft Store stub.
where py >nul 2>nul
if not errorlevel 1 goto run_py
where python >nul 2>nul
if not errorlevel 1 goto run_python
echo.
echo Python 3 is not installed, or not on PATH.
echo Get it from python.org and tick "Add python.exe to PATH" in the installer.
pause
exit /b 1
:run_py
py -3 -u bridge.py %*
goto done
:run_python
python -u bridge.py %*
:done
if errorlevel 1 pause
