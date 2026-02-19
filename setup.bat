@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo   Oscilloscope Capture — Environment Setup
echo ============================================================
echo.

:: ── Locate Python ────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo         Install Python 3.10+ from https://python.org
    echo         and make sure "Add Python to PATH" is checked.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Found %PY_VER%
echo.

:: ── Create virtual environment ───────────────────────────────
set VENV_DIR=%~dp0.venv

if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Virtual environment already exists at .venv
    echo        Skipping creation — upgrading packages only.
) else (
    echo [....] Creating virtual environment in .venv ...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK]   Virtual environment created.
)
echo.

:: ── Activate venv ────────────────────────────────────────────
call "%VENV_DIR%\Scripts\activate.bat"
echo [OK] Virtual environment activated.
echo.

:: ── Upgrade pip ──────────────────────────────────────────────
echo [....] Upgrading pip ...
python -m pip install --upgrade pip --quiet
echo [OK]   pip up to date.
echo.

:: ── Install requirements ─────────────────────────────────────
if not exist "%~dp0requirements.txt" (
    echo [ERROR] requirements.txt not found next to this script.
    pause
    exit /b 1
)

echo [....] Installing packages from requirements.txt ...
pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo [ERROR] One or more packages failed to install.
    echo         Check the output above for details.
    pause
    exit /b 1
)
echo.
echo [OK]   All packages installed successfully.
echo.

:: ── Summary ──────────────────────────────────────────────────
echo ============================================================
echo   Setup complete!
echo ============================================================
echo.
echo   To capture a screenshot:
echo     .venv\Scripts\python.exe lecroy_capture.py
echo.
echo   To scan for instruments:
echo     .venv\Scripts\python.exe scope_scanner.py
echo.
echo   Or activate the venv first, then just:
echo     python lecroy_capture.py
echo     python scope_scanner.py
echo.
pause
