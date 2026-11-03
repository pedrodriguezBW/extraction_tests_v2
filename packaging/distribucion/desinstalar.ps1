<# Elimina los accesos directos y la carpeta de instalacion del usuario actual. #>
$ErrorActionPreference = "Continue"
$AppName = "Generador de Informes"
$Target = Join-Path $env:LOCALAPPDATA "Programs\GeneradorInformes"

Add-Type -AssemblyName System.Windows.Forms
$answer = [System.Windows.Forms.MessageBox]::Show(
    "Se eliminara $AppName de este PC.`nLos informes y ensayos no se tocan.`n`nContinuar?",
    $AppName, [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Question)
if ($answer -ne [System.Windows.Forms.DialogResult]::Yes) { exit 0 }

Get-Process -Name "Generador de Informes" -ErrorAction SilentlyContinue | Stop-Process -Force
$targetPython = Join-Path $Target "python\python.exe"
Get-Process -Name python -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $targetPython } | Stop-Process -Force

Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath("Programs")) $AppName) -Recurse -Force -ErrorAction SilentlyContinue

# La carpeta se borra al terminar este proceso (el .bat se ejecuta desde ella).
Start-Process -FilePath "cmd.exe" -ArgumentList "/c timeout /t 2 /nobreak >nul & rmdir /s /q `"$Target`"" -WindowStyle Hidden
[System.Windows.Forms.MessageBox]::Show("$AppName se ha desinstalado.", $AppName) | Out-Null
