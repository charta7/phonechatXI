@echo off
rem phonechatXI bridge for Windows. /pchat start in game runs this.
title phonechatXI bridge
cd /d "%~dp0bridge"
python bridge.py %*
if errorlevel 1 pause
