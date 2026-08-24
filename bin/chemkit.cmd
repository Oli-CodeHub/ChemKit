@echo off
setlocal
set "ROOT=%~dp0.."
if exist "%ROOT%\.venv\Scripts\python.exe" (
  set "PYTHON=%ROOT%\.venv\Scripts\python.exe"
) else if exist "%ROOT%\venv\Scripts\python.exe" (
  set "PYTHON=%ROOT%\venv\Scripts\python.exe"
) else (
  where python >nul 2>&1 || (echo ChemKit requires Python 3.9+; run install.ps1 or install Python first.& exit /b 2)
  set "PYTHON=python"
)
"%PYTHON%" "%ROOT%\scripts\chemkit_cli.py" %*
