@echo off
setlocal

cd /d "%~dp0"

:: ── Abliterador All-in-One Launcher ──────────────────────────────────────
:: Configura automáticamente el firewall de Windows para acceso LAN y luego
:: arranca el servidor. La configuración del firewall requiere admin solo la
:: primera vez; el servidor puede correr sin admin.

set "EXE=%~dp0dist\AbliteradorAllInOne.exe"
set "PY_ENTRY=%~dp0abliterador_all_in_one.py"

:: ── 1. Detectar ejecutable o fallback Python ───────────────────────────
if exist "%EXE%" (
    set "LAUNCHER=%EXE%"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] No se encontro AbliteradorAllInOne.exe ni Python en PATH.
        echo Compila el ejecutable o instala Python y vuelve a intentarlo.
        pause
        exit /b 1
    )
    set "LAUNCHER=python %PY_ENTRY%"
)

:: ── 2. Configurar LAN como Administrador (primera vez o si faltan reglas) ─
echo.
echo [1/2] Configurando acceso LAN en Windows Firewall...
echo       (puede aparecer un dialogo de Control de Cuentas de Usuario - UAC)
echo.

:: PowerShell eleva el ejecutable con ShellExecute runas, espera a que termine
powershell -NoProfile -NonInteractive -Command ^
  "try { $proc = Start-Process -FilePath '%EXE%' -ArgumentList '--configure-lan' -Verb RunAs -PassThru -Wait; exit $proc.ExitCode } catch { Write-Host 'Elevacion cancelada o fallo'; exit 1 }" 2>nul

if errorlevel 1 (
    echo [AVISO] La configuracion de firewall fue omitida o cancelada.
    echo         El servidor iniciara de todas formas, pero puede no ser accesible desde LAN.
    echo         Para configurarlo manualmente ejecuta como Administrador:
    echo           netsh advfirewall firewall add rule name="AbliteradorNexus_HTTP_8088" dir=in action=allow protocol=TCP localport=8088 profile=any
    echo.
)

:: ── 3. Arrancar el servidor (sin elevar, usuario normal) ─────────────────
echo [2/2] Iniciando Abliterador All-in-One...
echo.

if exist "%EXE%" (
    start "" "%EXE%" --open-browser
) else (
    python "%PY_ENTRY%" --open-browser
)

endlocal
