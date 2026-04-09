@echo off
setlocal
cd /d "%~dp0"

set "APP=%~dp0main.py"
set "PYTHON_CMD="

if exist "%~dp0.venv\Scripts\pythonw.exe" (
    set "PYTHON_CMD=%~dp0.venv\Scripts\pythonw.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_CMD=%~dp0.venv\Scripts\python.exe"
)

if defined PYTHON_CMD (
    start "" "%PYTHON_CMD%" "%APP%"
    exit /b 0
)

where pyw >nul 2>nul
if not errorlevel 1 (
    start "" pyw -3 "%APP%"
    exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
    start "" py -3 "%APP%"
    exit /b 0
)

where pythonw >nul 2>nul
if not errorlevel 1 (
    start "" pythonw "%APP%"
    exit /b 0
)

where python >nul 2>nul
if not errorlevel 1 (
    start "" python "%APP%"
    exit /b 0
)

echo Python was not found.
echo Install Python 3.9+ or create .venv in this project.
pause
exit /b 1
