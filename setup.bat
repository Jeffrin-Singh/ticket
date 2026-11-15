@echo off
title Setup & Check Dependencies
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ---- ANSI colors ----
for /f %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"
set "GREEN=%ESC%[92m"
set "RED=%ESC%[91m"
set "YELLOW=%ESC%[93m"
set "CYAN=%ESC%[96m"
set "RESET=%ESC%[0m"

echo =================================================
echo  %CYAN% Tirupati Balaji – Dependency Installer %RESET%
echo =================================================
echo.

:: ---------- Check Python ----------
python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Python is not installed or not in PATH.
    echo Please install Python 3.8+ and add it to PATH.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('python --version 2^>^&1') do set "pyver=%%v"
echo %GREEN%[OK]%RESET% Python found: %pyver%
echo.

:: ---------- Upgrade pip ----------
echo %CYAN%Upgrading pip...%RESET%
python -m pip install --upgrade pip >nul 2>&1
echo %GREEN%[OK]%RESET% pip upgraded.
echo.

:: ---------- Check requirements.txt ----------
if not exist requirements.txt (
    echo %RED%[ERROR]%RESET% requirements.txt not found in this folder.
    echo Please place the file and try again.
    pause
    exit /b 1
)

:: ---------- Install missing packages ----------
echo %CYAN%Installing packages from requirements.txt ...%RESET%
echo (This may take several minutes...)
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Some packages failed to install.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)
echo.
echo %GREEN%[OK]%RESET% Installation completed.
echo.

:: ---------- Verify each package ----------
echo %CYAN%Verifying installed packages...%RESET%
echo.
set MISSING=0
for /f "usebackq eol=# delims=" %%p in ("requirements.txt") do (
    set "pkg=%%p"
    if not "!pkg!"=="" (
        for /f "usebackq tokens=1 delims=><=~ " %%a in ('!pkg!') do set "pkg_name=%%a"
        pip show "!pkg_name!" >nul 2>&1
        if errorlevel 1 (
            if "!pkg_name!"=="psycopg2" (
                pip show "psycopg2-binary" >nul 2>&1
                if errorlevel 1 (
                    echo %RED%[MISSING]%RESET% !pkg!
                    set /a MISSING+=1
                ) else (
                    echo %GREEN%[OK]%RESET% !pkg! (via psycopg2-binary)
                )
            ) else (
                echo %RED%[MISSING]%RESET% !pkg!
                set /a MISSING+=1
            )
        ) else (
            echo %GREEN%[OK]%RESET% !pkg!
        )
    )
)

echo.
if %MISSING% EQU 0 (
    echo %GREEN%[SUCCESS]%RESET% All dependencies are installed!
    echo.
    echo %YELLOW%You can now run the automation manually: %RESET%
    echo   python launcher.py
    echo.
    :: Show popup
    powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('All dependencies are installed successfully!`nYou can now run launcher.py.','Ready','OK','Information')" >nul 2>&1
) else (
    echo %RED%[FAIL]%RESET% %MISSING% package(s) could not be installed.
    echo Please install them manually with:
    echo   pip install -r requirements.txt
    echo.
    powershell -Command "Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('%MISSING% package(s) are still missing. Please install manually.','Error','OK','Error')" >nul 2>&1
    pause
    exit /b 1
)

pause