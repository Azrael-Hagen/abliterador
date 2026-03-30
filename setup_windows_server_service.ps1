param(
    [ValidateSet("install", "remove")]
    [string]$Action = "install",
    [string]$ServiceName = "AbliteradorAllInOne",
    [int]$Port = 8088,
    [string]$Host = "0.0.0.0"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExePath = Join-Path $ProjectRoot "dist\AbliteradorAllInOne.exe"
$NssmDefaultPath = "C:\tools\nssm\nssm.exe"
$TaskName = "AbliteradorAllInOneStartup"

function Test-Administrator {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Install-WithNssm {
    param([string]$NssmPath)

    & $NssmPath install $ServiceName $ExePath
    & $NssmPath set $ServiceName AppParameters ""
    & $NssmPath set $ServiceName AppDirectory $ProjectRoot
    & $NssmPath set $ServiceName Start SERVICE_AUTO_START
    & $NssmPath set $ServiceName AppStdout (Join-Path $ProjectRoot "logs\service_stdout.log")
    & $NssmPath set $ServiceName AppStderr (Join-Path $ProjectRoot "logs\service_stderr.log")

    sc.exe description $ServiceName "Abliterador all-in-one web server"
    Start-Service -Name $ServiceName
    Write-Host "Servicio instalado y arrancado con NSSM: $ServiceName"
}

function Remove-WithNssm {
    param([string]$NssmPath)

    if (Get-Service -Name $ServiceName -ErrorAction SilentlyContinue) {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    }
    & $NssmPath remove $ServiceName confirm
    Write-Host "Servicio eliminado con NSSM: $ServiceName"
}

function Install-WithScheduledTask {
    $python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    $launcher = Join-Path $ProjectRoot "abliterador_all_in_one.py"

    if (-not (Test-Path $python)) {
        throw "No se encontro .venv\\Scripts\\python.exe para el modo tarea programada."
    }
    if (-not (Test-Path $launcher)) {
        throw "No se encontro abliterador_all_in_one.py."
    }

    $command = "`"$python`" `"$launcher`""
    $arg = "/Create /F /SC ONSTART /RU SYSTEM /RL HIGHEST /TN `"$TaskName`" /TR `"$command`""
    Start-Process -FilePath schtasks.exe -ArgumentList $arg -NoNewWindow -Wait
    Start-Process -FilePath schtasks.exe -ArgumentList "/Run /TN `"$TaskName`"" -NoNewWindow -Wait

    Write-Host "Tarea programada creada y ejecutada: $TaskName"
}

function Remove-ScheduledTask {
    Start-Process -FilePath schtasks.exe -ArgumentList "/Delete /F /TN `"$TaskName`"" -NoNewWindow -Wait
    Write-Host "Tarea programada eliminada: $TaskName"
}

if (-not (Test-Administrator)) {
    throw "Ejecuta este script como Administrador."
}

if ($Action -eq "install") {
    if (-not (Test-Path $ExePath)) {
        throw "No se encontro $ExePath. Compila primero con: python build_installer.py --onefile --all-in-one"
    }

    [Environment]::SetEnvironmentVariable("ABLITERADOR_WEB_HOST", $Host, "Machine")
    [Environment]::SetEnvironmentVariable("ABLITERADOR_WEB_PORT", "$Port", "Machine")
    [Environment]::SetEnvironmentVariable("ABLITERADOR_LOCAL_NETWORK_ONLY", "1", "Machine")

    New-Item -ItemType Directory -Path (Join-Path $ProjectRoot "logs") -Force | Out-Null

    if (Test-Path $NssmDefaultPath) {
        Install-WithNssm -NssmPath $NssmDefaultPath
    }
    else {
        Write-Host "NSSM no encontrado en $NssmDefaultPath. Usando tarea programada como fallback."
        Install-WithScheduledTask
    }

    Write-Host ""
    Write-Host "Instalacion completada."
    Write-Host "URLs esperadas:"
    Write-Host "  - http://127.0.0.1:$Port"
    Write-Host "  - http://<IP-LAN-DEL-SERVIDOR>:$Port"
}
else {
    if (Test-Path $NssmDefaultPath) {
        Remove-WithNssm -NssmPath $NssmDefaultPath
    }
    else {
        Remove-ScheduledTask
    }
}
