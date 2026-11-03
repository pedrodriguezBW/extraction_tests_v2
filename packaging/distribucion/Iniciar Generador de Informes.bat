@echo off
rem Arranca el Generador de Informes (backend + interfaz). Doble clic.
start "" powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0launcher.ps1"
