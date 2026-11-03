@echo off
rem Instala (o actualiza) el Generador de Informes y lo abre. Doble clic.
rem No necesita permisos de administrador, Python, Node.js ni Rust.
echo Instalando el Generador de Informes...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
if errorlevel 1 (
    echo.
    echo La instalacion no se ha completado.
    pause
)
