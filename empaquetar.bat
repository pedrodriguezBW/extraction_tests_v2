@echo off
rem ==========================================================================
rem  Genera el paquete instalable del Generador de Informes.
rem  Doble clic en este archivo (en la raiz del repositorio).
rem  Opciones (desde consola):
rem    empaquetar.bat -Publicar          copia el ZIP y el manifiesto a la
rem                                      carpeta compartida ToolingVersions
rem    empaquetar.bat -PythonEmbedZip C:\ruta\python-3.12.x-embed-amd64.zip
rem    empaquetar.bat -OutputDir D:\Paquetes
rem ==========================================================================
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0packaging\build_package.ps1" %*
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" (
    echo  [ERROR] El empaquetado no se ha completado. Revisa los mensajes anteriores.
) else (
    echo  Empaquetado completado.
)
echo.
pause
exit /b %RESULT%
