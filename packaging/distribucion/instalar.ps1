<#
    Instala el Generador de Informes para el usuario actual (sin permisos de
    administrador):
      - copia el paquete a %LOCALAPPDATA%\Programs\GeneradorInformes,
      - crea accesos directos en el Escritorio y en el menu Inicio,
      - arranca la aplicacion.
    Volver a ejecutarlo con un paquete nuevo actualiza la instalacion.
#>
$ErrorActionPreference = "Stop"

$AppName = "Generador de Informes"
$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $env:LOCALAPPDATA "Programs\GeneradorInformes"
$UiProcessName = "Generador de Informes"

Add-Type -AssemblyName System.Windows.Forms

function Show-Message([string]$Message, [System.Windows.Forms.MessageBoxIcon]$Icon) {
    [System.Windows.Forms.MessageBox]::Show(
        $Message, $AppName,
        [System.Windows.Forms.MessageBoxButtons]::OK, $Icon) | Out-Null
}

function New-Shortcut([string]$Path, [string]$Target, [string]$Arguments, [string]$WorkDir, [string]$Icon) {
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($Path)
    $link.TargetPath = $Target
    $link.Arguments = $Arguments
    $link.WorkingDirectory = $WorkDir
    $link.IconLocation = "$Icon,0"
    $link.WindowStyle = 7
    $link.Description = $AppName
    $link.Save()
}

try {
    $version = (Get-Content -LiteralPath (Join-Path $Source "VERSION.txt") -ErrorAction SilentlyContinue | Select-Object -First 1)
    if (-not (Test-Path -LiteralPath (Join-Path $Source "python\python.exe"))) {
        throw "No se encuentran los archivos del programa junto a Instalar.bat.`n`nSi lo has abierto desde dentro del ZIP, primero descomprime el ZIP (clic derecho > Extraer todo) y ejecuta Instalar.bat desde la carpeta extraida."
    }

    Write-Host "Instalando $AppName $version en $Target ..."

    # Cierra una version anterior en ejecucion para poder reemplazarla.
    Get-Process -Name $UiProcessName -ErrorAction SilentlyContinue | Stop-Process -Force
    $targetPython = Join-Path $Target "python\python.exe"
    Get-Process -Name python -ErrorAction SilentlyContinue |
        Where-Object { $_.Path -eq $targetPython } | Stop-Process -Force
    Start-Sleep -Milliseconds 500

    $sameFolder = [string]::Equals(
        [System.IO.Path]::GetFullPath($Source).TrimEnd('\'),
        [System.IO.Path]::GetFullPath($Target).TrimEnd('\'),
        [System.StringComparison]::OrdinalIgnoreCase)
    if (-not $sameFolder) {
        New-Item -ItemType Directory -Force -Path $Target | Out-Null
        # /MIR: deja la carpeta identica al paquete (elimina restos de versiones anteriores).
        & robocopy $Source $Target /MIR /NFL /NDL /NJH /NJS /NP /R:2 /W:1 | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "No se pudieron copiar los archivos (robocopy $LASTEXITCODE)." }
    }

    # Quita la marca "descargado de Internet" para que Windows no bloquee los scripts.
    Get-ChildItem -LiteralPath $Target -Recurse -File | Unblock-File -ErrorAction SilentlyContinue

    $powershell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    $launcherArgs = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$(Join-Path $Target 'launcher.ps1')`""
    $icon = Join-Path $Target "ui\Generador de Informes.exe"

    $desktop = [Environment]::GetFolderPath("Desktop")
    $startMenu = Join-Path ([Environment]::GetFolderPath("Programs")) $AppName
    New-Item -ItemType Directory -Force -Path $startMenu | Out-Null

    New-Shortcut (Join-Path $desktop "$AppName.lnk") $powershell $launcherArgs $Target $icon
    New-Shortcut (Join-Path $startMenu "$AppName.lnk") $powershell $launcherArgs $Target $icon
    New-Shortcut (Join-Path $startMenu "Desinstalar $AppName.lnk") (Join-Path $Target "Desinstalar.bat") "" $Target "$env:SystemRoot\System32\shell32.dll"

    Write-Host "Instalacion completada. Abriendo la aplicacion..."
    Start-Process -FilePath $powershell -ArgumentList $launcherArgs -WindowStyle Hidden
    exit 0
} catch {
    Show-Message ("No se pudo completar la instalacion:`n`n" + $_.Exception.Message) ([System.Windows.Forms.MessageBoxIcon]::Error)
    exit 1
}
