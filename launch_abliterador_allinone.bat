@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

:: ═══════════════════════════════════════════════════════════════════════
::  Abliterador All-in-One Launcher
::  • Wizard automático de configuración inicial (.abliterador.env)
::  • Configuración de firewall Windows (UAC, solo una vez)
::  • Lanzamiento del servidor con apertura de navegador
:: ═══════════════════════════════════════════════════════════════════════

set "EXE=%~dp0dist\AbliteradorAllInOne.exe"
set "PY_ENTRY=%~dp0abliterador_all_in_one.py"
set "ENV_FILE=%~dp0.abliterador.env"
set "WIZARD_FLAG="

:: ── 1. Detectar ejecutable o fallback Python ──────────────────────────
if exist "%EXE%" (
    set "RUN_EXE=1"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo.
        echo  [ERROR] No se encontro AbliteradorAllInOne.exe ni Python en PATH.
        echo  Compila el ejecutable o instala Python y vuelve a intentarlo.
        echo.
        pause
        exit /b 1
    )
    set "RUN_EXE=0"
)

:: ── 2. Primera ejecución: flag --wizard para configuración inicial ─────
if not exist "%ENV_FILE%" (
    set "WIZARD_FLAG=--wizard"
    echo.
    echo  ╔══════════════════════════════════════════════════════════════╗
    echo  ║   Primera ejecución detectada – Wizard de configuración      ║
    echo  ╚══════════════════════════════════════════════════════════════╝
    echo.
)

:: ── 3. Configurar LAN Firewall como Administrador ─────────────────────
echo  [1/2] Verificando reglas de Firewall para acceso LAN...
echo        (puede aparecer un dialogo UAC - Control de Cuentas de Usuario)
echo.

if "%RUN_EXE%"=="1" (
    powershell -NoProfile -NonInteractive -Command ^
      "try { $proc = Start-Process -FilePath '%EXE%' -ArgumentList '--configure-lan' -Verb RunAs -PassThru -Wait; exit $proc.ExitCode } catch { exit 1 }" 2>nul
) else (
    powershell -NoProfile -NonInteractive -Command ^
      "try { $proc = Start-Process 'python' -ArgumentList '%PY_ENTRY% --configure-lan' -Verb RunAs -PassThru -Wait; exit $proc.ExitCode } catch { exit 1 }" 2>nul
)

if errorlevel 1 (
    echo  [AVISO] Firewall no configurado ^(UAC cancelado o sin permisos^).
    echo          El servidor intentara arrancar de todas formas.
    echo          Para acceso LAN manual, ejecuta como Administrador:
    echo            netsh advfirewall firewall add rule name="AbliteradorNexus_HTTP_8088" ^
    echo              dir=in action=allow protocol=TCP localport=8088 profile=any
    echo.
) else (
    echo  [OK] Firewall configurado correctamente.
    echo.
)

:: ── 4. Arrancar servidor con wizard si corresponde ────────────────────
echo  [2/2] Iniciando Abliterador All-in-One...
echo.

if "%RUN_EXE%"=="1" (
    start "AbliteradorNexus" "%EXE%" --open-browser %WIZARD_FLAG%
) else (
    start "AbliteradorNexus" /B python "%PY_ENTRY%" --open-browser %WIZARD_FLAG%
)

echo  Servidor iniciado. Revisa la ventana de consola del servidor.
echo  Si es primera vez, responde las preguntas de configuracion en esa ventana.
echo.
echo  Cierra esta ventana cuando quieras.
timeout /t 5 /nobreak >nul
endlocal

