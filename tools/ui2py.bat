@echo off
setlocal

pyuic6 %~dp0\..\app\ui\app.ui -o %~dp0\..\app\ui\appgui.py
pyuic6 %~dp0\..\app\ui\setting.ui -o %~dp0\..\app\ui\appsettinggui.py