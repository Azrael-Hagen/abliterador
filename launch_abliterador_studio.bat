@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python no esta disponible en PATH.
  echo Instala Python o activa tu entorno virtual antes de ejecutar este launcher.
  pause
  exit /b 1
)

python "%~dp0abliterador_studio.py"
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
  echo.
  echo La aplicacion finalizo con codigo de error %EXIT_CODE%.
  pause
)

exit /b %EXIT_CODE%
