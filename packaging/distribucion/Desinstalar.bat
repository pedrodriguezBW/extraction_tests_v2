@echo off
rem Desinstala el Generador de Informes del usuario actual.
copy /y "%~dp0desinstalar.ps1" "%TEMP%\generador-informes-desinstalar.ps1" >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\generador-informes-desinstalar.ps1"
