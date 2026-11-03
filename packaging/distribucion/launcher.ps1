<#
    Arranca el Generador de Informes instalado:
      1. inicia el backend (Python embebido + FastAPI) oculto en 127.0.0.1:8000,
      2. espera a que responda /health,
      3. abre la interfaz de escritorio,
      4. al cerrar la interfaz, detiene el backend.
    Registros: %LOCALAPPDATA%\GeneradorInformes\logs
#>
$ErrorActionPreference = "Stop"

$AppName = "Generador de Informes"
$BackendPort = 8000
$HealthUrl = "http://127.0.0.1:$BackendPort/health"
$ApplicationId = "climatic-report-generator"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $Root "python\python.exe"
$AppDir = Join-Path $Root "app"
$UiExe = Join-Path $Root "ui\Generador de Informes.exe"
$TemplateDir = Join-Path $Root "plantilla"
$LogDir = Join-Path $env:LOCALAPPDATA "GeneradorInformes\logs"

Add-Type -AssemblyName System.Windows.Forms

function Show-Error([string]$Message) {
    [System.Windows.Forms.MessageBox]::Show(
        $Message, $AppName,
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error) | Out-Null
}

function Get-Health {
    try {
        return Invoke-RestMethod -Uri $HealthUrl -TimeoutSec 2
    } catch {
        return $null
    }
}

function Test-PortInUse([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        return ($async.AsyncWaitHandle.WaitOne(500) -and $client.Connected)
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

$backend = $null
try {
    foreach ($required in @($PythonExe, $UiExe, $AppDir)) {
        if (-not (Test-Path -LiteralPath $required)) {
            throw "La instalacion esta incompleta: falta $required.`nVuelve a ejecutar Instalar.bat."
        }
    }

    # Una sola ventana: si la interfaz ya esta abierta, no se lanza otra.
    $uiProcessName = [System.IO.Path]::GetFileNameWithoutExtension($UiExe)
    if (Get-Process -Name $uiProcessName -ErrorAction SilentlyContinue) {
        [System.Windows.Forms.MessageBox]::Show(
            "$AppName ya esta abierto.", $AppName,
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Information) | Out-Null
        exit 0
    }

    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    $ownsBackend = $false

    $health = Get-Health
    if ($health -and $health.application -eq $ApplicationId) {
        # Ya hay un backend del generador en marcha (p. ej. uno anterior que
        # no se cerro): se reutiliza.
    } elseif (Test-PortInUse $BackendPort) {
        throw "El puerto $BackendPort esta ocupado por otro programa.`nCierralo (o reinicia el PC) y vuelve a intentarlo."
    } else {
        $template = Get-ChildItem -LiteralPath $TemplateDir -Filter "*.pptx" -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($template) { $env:REPORT_TEMPLATE_PATH = $template.FullName }
        $env:MPLBACKEND = "Agg"
        $env:PYTHONUTF8 = "1"
        $env:PYTHONDONTWRITEBYTECODE = "1"

        $stdout = Join-Path $LogDir "backend.out.log"
        $stderr = Join-Path $LogDir "backend.err.log"
        $backend = Start-Process -FilePath $PythonExe `
            -ArgumentList @("-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort") `
            -WorkingDirectory $AppDir -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $ownsBackend = $true

        $deadline = (Get-Date).AddSeconds(90)
        $health = $null
        while ((Get-Date) -lt $deadline -and -not $backend.HasExited) {
            Start-Sleep -Milliseconds 500
            $health = Get-Health
            if ($health) { break }
        }
        if (-not $health) {
            $tail = Get-Content -LiteralPath $stderr -Tail 15 -ErrorAction SilentlyContinue | Out-String
            throw "El servicio interno no ha arrancado.`n`nRegistro: $stderr`n`n$tail"
        }
    }

    $ui = Start-Process -FilePath $UiExe -WorkingDirectory (Split-Path -Parent $UiExe) -PassThru
    $ui.WaitForExit()
} catch {
    Show-Error $_.Exception.Message
    exit 1
} finally {
    if ($backend -and -not $backend.HasExited) {
        Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
    }
}
exit 0
