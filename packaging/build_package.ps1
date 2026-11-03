<#
.SYNOPSIS
    Construye el paquete instalable del Generador de Informes.

.DESCRIPTION
    Se ejecuta en el PC de desarrollo (el que ya tiene Python, Node.js y Rust).
    Produce una carpeta y un ZIP autocontenidos que cualquier usuario puede
    instalar con un doble clic en "Instalar.bat", sin Python, Node ni Rust:

      GeneradorInformes-<version>\
        Instalar.bat                        instala y crea los accesos directos
        Iniciar Generador de Informes.bat   arranca backend + interfaz
        Desinstalar.bat
        launcher.ps1 / instalar.ps1 / desinstalar.ps1
        python\     Python embebido con todas las dependencias
        app\        backend FastAPI + motor de informes
        plantilla\  plantilla PowerPoint corporativa
        ui\         ejecutable de escritorio (Tauri, modo release)

    Ademas genera generador-informes-<version>.zip y el manifiesto
    generador-informes.json listo para la carpeta compartida.
#>
[CmdletBinding()]
param(
    # Carpeta de salida (fuera de OneDrive para no sincronizar cientos de MB).
    [string]$OutputDir = (Join-Path $env:USERPROFILE "GeneradorInformes-paquetes"),

    # ZIP "Windows embeddable package (64-bit)" ya descargado de python.org.
    # Util si el proxy impide la descarga automatica. Debe coincidir en
    # version con el Python usado para instalar dependencias.
    [string]$PythonEmbedZip = "",

    # Python con el que se descargan las dependencias. Por defecto, el .venv
    # del repositorio; si no existe, el lanzador "py -3" o "python".
    [string]$PythonExe = "",

    # Copia el ZIP y el manifiesto a la carpeta compartida de versiones.
    [switch]$Publicar,

    # Reutiliza el ejecutable de la interfaz ya compilado (no recompila Tauri).
    [switch]$SinCompilarInterfaz
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$SharedVersionsDir = "\\vigvsfil1.global.borgwarner.net\vigproductengineering\Documentacion_I+D\R&T\ToolingVersions"
$UiExeName = "Generador de Informes.exe"
$BackendPort = 8000

$RepoRoot = Split-Path -Parent $PSScriptRoot
$DistributionTemplates = Join-Path $PSScriptRoot "distribucion"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "[ERROR] $Message" -ForegroundColor Red
    exit 1
}

function Invoke-Checked([string]$FilePath, [string[]]$Arguments, [string]$What) {
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        Fail "$What ha fallado (codigo $LASTEXITCODE)."
    }
}

function Write-Utf8NoBom([string]$Path, [string]$Text) {
    [System.IO.File]::WriteAllText($Path, $Text, (New-Object System.Text.UTF8Encoding($false)))
}

function Copy-Tree([string]$Source, [string]$Destination) {
    # robocopy: 0-7 = exito; excluye caches y entornos.
    & robocopy $Source $Destination /E /NFL /NDL /NJH /NJS /NP `
        /XD "__pycache__" ".pytest_cache" ".mypy_cache" ".venv" "node_modules" `
        /XF "*.pyc" "*.pyo" "~$*" | Out-Null
    if ($LASTEXITCODE -ge 8) {
        Fail "No se pudo copiar $Source (robocopy $LASTEXITCODE)."
    }
    $global:LASTEXITCODE = 0
}

function Test-PortInUse([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        $connected = $async.AsyncWaitHandle.WaitOne(500) -and $client.Connected
        return $connected
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

Set-Location $RepoRoot
Write-Host "Generador de Informes - empaquetado" -ForegroundColor Green
Write-Host "Repositorio: $RepoRoot"

# --------------------------------------------------------------------------
Write-Step "Comprobando version"
$versionFile = Join-Path $RepoRoot "src\report_generator\version.py"
$versionMatch = Select-String -Path $versionFile -Pattern '__version__\s*=\s*"([^"]+)"'
if (-not $versionMatch) { Fail "No se encontro __version__ en $versionFile." }
$Version = $versionMatch.Matches[0].Groups[1].Value
Write-Host "Version del backend: $Version"

$tauriConfPath = Join-Path $RepoRoot "frontend\src-tauri\tauri.conf.json"
$tauriVersion = (Get-Content $tauriConfPath -Raw | ConvertFrom-Json).version
if ($tauriVersion -ne $Version) {
    Fail "La version de tauri.conf.json ($tauriVersion) no coincide con version.py ($Version). Igualalas antes de empaquetar."
}
$packageJsonVersion = (Get-Content (Join-Path $RepoRoot "frontend\package.json") -Raw | ConvertFrom-Json).version
if ($packageJsonVersion -ne $Version) {
    Write-Host "Aviso: frontend\package.json tiene la version $packageJsonVersion (backend $Version)." -ForegroundColor Yellow
}

# --------------------------------------------------------------------------
Write-Step "Buscando Python"
if (-not $PythonExe) {
    $venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $PythonExe = $venvPython
    } elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonExe = (& py -3 -c "import sys; print(sys.executable)").Trim()
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonExe = (Get-Command python).Source
    } else {
        Fail "No se encontro Python. Indica uno con -PythonExe."
    }
}
$pyInfo = (& $PythonExe -c "import sys, struct; print('%d.%d.%d %d' % (sys.version_info[0], sys.version_info[1], sys.version_info[2], struct.calcsize('P') * 8))").Trim()
if ($LASTEXITCODE -ne 0) { Fail "No se pudo ejecutar $PythonExe." }
$PyVersion, $PyBits = $pyInfo -split " "
if ($PyBits -ne "64") { Fail "Se necesita un Python de 64 bits (encontrado: $PyBits bits)." }
$PyMajorMinor = ($PyVersion -split "\.")[0..1] -join ""
Write-Host "Python: $PythonExe ($PyVersion, 64 bits)"

foreach ($tool in @("npm", "cargo")) {
    if (-not $SinCompilarInterfaz -and -not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Fail "No se encontro '$tool' en el PATH. Es necesario para compilar la interfaz."
    }
}

# --------------------------------------------------------------------------
$PackageName = "GeneradorInformes-$Version"
$Stage = Join-Path $OutputDir $PackageName
$CacheDir = Join-Path $OutputDir "_cache"
New-Item -ItemType Directory -Force -Path $OutputDir, $CacheDir | Out-Null
if (Test-Path $Stage) {
    Write-Host "Eliminando paquete anterior: $Stage"
    Remove-Item -Recurse -Force $Stage
}
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

# --------------------------------------------------------------------------
Write-Step "Preparando Python embebido $PyVersion"
if (-not $PythonEmbedZip) {
    $PythonEmbedZip = Join-Path $CacheDir "python-$PyVersion-embed-amd64.zip"
    if (-not (Test-Path $PythonEmbedZip)) {
        $url = "https://www.python.org/ftp/python/$PyVersion/python-$PyVersion-embed-amd64.zip"
        Write-Host "Descargando $url"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        [Net.WebRequest]::DefaultWebProxy.Credentials = [Net.CredentialCache]::DefaultNetworkCredentials
        try {
            Invoke-WebRequest -Uri $url -OutFile $PythonEmbedZip -UseBasicParsing
        } catch {
            if (Test-Path $PythonEmbedZip) { Remove-Item $PythonEmbedZip -Force }
            Fail "No se pudo descargar Python embebido ($($_.Exception.Message)). Descargalo a mano desde $url y vuelve a ejecutar con -PythonEmbedZip <ruta>."
        }
    } else {
        Write-Host "Usando copia en cache: $PythonEmbedZip"
    }
}
if (-not (Test-Path $PythonEmbedZip)) { Fail "No existe $PythonEmbedZip." }
$PythonDir = Join-Path $Stage "python"
Expand-Archive -Path $PythonEmbedZip -DestinationPath $PythonDir -Force
$pthFile = Get-ChildItem -Path $PythonDir -Filter "python*._pth" | Select-Object -First 1
if (-not $pthFile) { Fail "El ZIP de Python embebido no contiene el archivo ._pth." }
if ($pthFile.Name -ne "python$PyMajorMinor._pth") {
    Fail "El Python embebido ($($pthFile.Name)) no coincide con Python $PyVersion. Usa el ZIP de la misma version."
}
# Rutas de busqueda: biblioteca estandar, dependencias y codigo de la app.
$pthText = @(
    "python$PyMajorMinor.zip",
    ".",
    "Lib\site-packages",
    "..\app",
    "import site"
) -join "`r`n"
Write-Utf8NoBom $pthFile.FullName ($pthText + "`r`n")

# --------------------------------------------------------------------------
Write-Step "Instalando dependencias de Python en el paquete"
$SitePackages = Join-Path $PythonDir "Lib\site-packages"
New-Item -ItemType Directory -Force -Path $SitePackages | Out-Null
Invoke-Checked $PythonExe @(
    "-m", "pip", "install",
    "--target", $SitePackages,
    "--only-binary=:all:",
    "--no-warn-script-location",
    "--disable-pip-version-check",
    "-r", (Join-Path $RepoRoot "requirements.txt")
) "La instalacion de dependencias (pip)"
# Ejecutables de consola de pip --target: no se usan y llevan rutas absolutas.
$binDir = Join-Path $SitePackages "bin"
if (Test-Path $binDir) { Remove-Item -Recurse -Force $binDir }

# --------------------------------------------------------------------------
Write-Step "Copiando el codigo de la aplicacion"
$AppDir = Join-Path $Stage "app"
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
Copy-Tree (Join-Path $RepoRoot "backend") (Join-Path $AppDir "backend")
Copy-Tree (Join-Path $RepoRoot "src") (Join-Path $AppDir "src")
foreach ($file in @("config.py", "requirements.txt", "generate_report.py", "run_pipeline.py")) {
    $sourceFile = Join-Path $RepoRoot $file
    if (Test-Path $sourceFile) { Copy-Item $sourceFile $AppDir }
}

# --------------------------------------------------------------------------
Write-Step "Copiando la plantilla PowerPoint"
$templateSource = (& $PythonExe -c "import config; print(config.POWERPOINT_TEMPLATE_PATH)").Trim()
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $templateSource)) {
    Fail "No se encuentra la plantilla configurada en config.py: $templateSource"
}
$TemplateDir = Join-Path $Stage "plantilla"
New-Item -ItemType Directory -Force -Path $TemplateDir | Out-Null
Copy-Item -LiteralPath $templateSource -Destination $TemplateDir
Write-Host "Plantilla: $(Split-Path -Leaf $templateSource)"

# --------------------------------------------------------------------------
$FrontendDir = Join-Path $RepoRoot "frontend"
$ReleaseExe = Join-Path $FrontendDir "src-tauri\target\release\climatic-report-generator.exe"
if (-not $SinCompilarInterfaz) {
    Write-Step "Compilando la interfaz de escritorio (puede tardar varios minutos)"
    Push-Location $FrontendDir
    try {
        if (-not (Test-Path (Join-Path $FrontendDir "node_modules"))) {
            Invoke-Checked "npm" @("ci") "npm ci"
        }
        # La interfaz empaquetada siempre habla con el backend local.
        $env:VITE_API_BASE_URL = "http://127.0.0.1:$BackendPort"
        Invoke-Checked "npm" @("run", "tauri", "--", "build", "--no-bundle") "La compilacion de Tauri"
    } finally {
        Remove-Item Env:\VITE_API_BASE_URL -ErrorAction SilentlyContinue
        Pop-Location
    }
}
if (-not (Test-Path $ReleaseExe)) {
    $candidate = Get-ChildItem (Join-Path $FrontendDir "src-tauri\target\release") -Filter "*.exe" -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notlike "build-script*" } | Select-Object -First 1
    if (-not $candidate) { Fail "No se encontro el ejecutable compilado en src-tauri\target\release." }
    $ReleaseExe = $candidate.FullName
}
$UiDir = Join-Path $Stage "ui"
New-Item -ItemType Directory -Force -Path $UiDir | Out-Null
Copy-Item $ReleaseExe (Join-Path $UiDir $UiExeName)
Write-Host "Interfaz: $ReleaseExe"

# --------------------------------------------------------------------------
Write-Step "Anadiendo instalador y lanzador"
Copy-Item (Join-Path $DistributionTemplates "*") $Stage -Recurse -Force
Write-Utf8NoBom (Join-Path $Stage "VERSION.txt") "$Version`r`n"

# --------------------------------------------------------------------------
Write-Step "Verificando el paquete"
$StagePython = Join-Path $PythonDir "python.exe"
Push-Location $env:TEMP
try {
    Invoke-Checked $StagePython @("-c", "import backend.app.main, pptx, matplotlib, pandas, numpy, PIL, uvicorn; print('Importaciones correctas')") "La prueba de importacion"
} finally {
    Pop-Location
}

if (Test-PortInUse $BackendPort) {
    Write-Host "Aviso: el puerto $BackendPort esta ocupado (backend de desarrollo abierto?). Se omite la prueba de arranque." -ForegroundColor Yellow
} else {
    $logOut = Join-Path $env:TEMP "generador-informes-prueba.out.log"
    $logErr = Join-Path $env:TEMP "generador-informes-prueba.err.log"
    $env:REPORT_TEMPLATE_PATH = (Get-ChildItem $TemplateDir -Filter "*.pptx" | Select-Object -First 1).FullName
    $env:MPLBACKEND = "Agg"
    $backend = Start-Process -FilePath $StagePython `
        -ArgumentList @("-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "$BackendPort") `
        -WorkingDirectory $AppDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $logOut -RedirectStandardError $logErr
    $healthy = $false
    try {
        for ($i = 0; $i -lt 60 -and -not $backend.HasExited; $i++) {
            Start-Sleep -Milliseconds 500
            try {
                $health = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/health" -TimeoutSec 2
                if ($health.status -eq "ok" -and $health.version -eq $Version) { $healthy = $true; break }
            } catch { }
        }
    } finally {
        if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
        Remove-Item Env:\REPORT_TEMPLATE_PATH, Env:\MPLBACKEND -ErrorAction SilentlyContinue
    }
    if (-not $healthy) {
        Write-Host (Get-Content $logErr -Tail 30 -ErrorAction SilentlyContinue | Out-String)
        Fail "El backend empaquetado no respondio en /health."
    }
    Write-Host "Backend empaquetado arranca y responde correctamente."
}

# --------------------------------------------------------------------------
Write-Step "Creando el ZIP"
$ZipName = "generador-informes-$Version.zip"
$ZipPath = Join-Path $OutputDir $ZipName
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $Stage, $ZipPath, [System.IO.Compression.CompressionLevel]::Optimal, $true)
$zipSizeMb = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host "ZIP: $ZipPath ($zipSizeMb MB)"

$ManifestPath = Join-Path $OutputDir "generador-informes.json"
$manifest = [ordered]@{
    version = $Version
    package = (Join-Path $SharedVersionsDir $ZipName)
}
Write-Utf8NoBom $ManifestPath (($manifest | ConvertTo-Json) + "`n")
Write-Host "Manifiesto: $ManifestPath"

# --------------------------------------------------------------------------
if ($Publicar) {
    Write-Step "Publicando en la carpeta compartida"
    if (-not (Test-Path $SharedVersionsDir)) { Fail "No se puede acceder a $SharedVersionsDir." }
    Copy-Item $ZipPath $SharedVersionsDir -Force
    # El manifiesto se copia el ultimo: solo anuncia la version cuando el ZIP ya esta.
    Copy-Item $ManifestPath $SharedVersionsDir -Force
    Write-Host "Publicado: $(Join-Path $SharedVersionsDir $ZipName)"
}

Write-Host ""
Write-Host "Paquete listo." -ForegroundColor Green
Write-Host "  Carpeta : $Stage"
Write-Host "  ZIP     : $ZipPath"
Write-Host "Para instalar en otro PC: descomprimir el ZIP y doble clic en Instalar.bat."
if (-not $Publicar) {
    Write-Host "Para distribuirlo: copia el ZIP y generador-informes.json a $SharedVersionsDir (o ejecuta empaquetar.bat -Publicar)."
}
Start-Process explorer.exe $OutputDir
exit 0
