@echo off
setlocal EnableExtensions

rem FiscalOps CFDI Reader - launcher without EXE packaging.
rem The virtual environment stays inside this repository and does not need admin rights.
cd /d "%~dp0"
set "APP_ROOT=%CD%"
set "VENV_DIR=%APP_ROOT%\.venv"
set "PYTHONUTF8=1"
set "PYTHONNOUSERSITE=1"

if exist "%VENV_DIR%\Scripts\python.exe" goto launch

echo [FiscalOps] No se encontro un entorno local. Preparando .venv...
set "BOOTSTRAP="
py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
if not errorlevel 1 set "BOOTSTRAP=py -3.11"
if not defined BOOTSTRAP (
  python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)" >nul 2>&1
  if not errorlevel 1 set "BOOTSTRAP=python"
)
if not defined BOOTSTRAP (
  echo.
  echo No se encontro Python 3.11 de 64 bits.
  echo Instala Python 3.11 para tu usuario y vuelve a ejecutar este archivo.
  echo No se requiere un EXE de FiscalOps ni permisos de administrador.
  pause
  exit /b 2
)

call %BOOTSTRAP% -m venv "%VENV_DIR%"
if errorlevel 1 goto setup_error

echo [FiscalOps] Instalando dependencias fijadas de requirements\desktop.txt...
"%VENV_DIR%\Scripts\python.exe" -m pip install --require-hashes -r requirements\desktop.txt
if errorlevel 1 goto setup_error

:launch
echo [FiscalOps] Iniciando CFDI Reader...
"%VENV_DIR%\Scripts\python.exe" -m app.desktop.main
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo FiscalOps termino con codigo %EXIT_CODE%.
  pause
)
exit /b %EXIT_CODE%

:setup_error
echo.
echo No fue posible preparar el entorno local.
echo Revisa el acceso a PyPI o instala las dependencias manualmente con:
echo   .venv\Scripts\python.exe -m pip install --require-hashes -r requirements\desktop.txt
pause
exit /b 3
