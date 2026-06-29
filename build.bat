@echo off
title Alien Launcher Builder
cls

echo ============================================================
echo                  Alien Launcher Local Builder
echo ============================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your PATH.
    echo Please install Python and try again.
    pause
    exit /b 1
)

:: Check if virtual environment is active, otherwise suggest/install dependencies
echo Checking dependencies...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing PyInstaller...
    pip install pyinstaller
)

echo.
echo Installing requirements from requirements.txt...
pip install -r requirements.txt

echo.
echo Cleaning up old build/dist directories...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo.
echo Starting compilation with PyInstaller...
echo This may take a minute...
echo.

python -m PyInstaller "Alien Launcher.spec" --clean -y

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Compilation failed. Please check the errors above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS: Compilation completed successfully!
echo.
echo Output executable location:
echo dist\Alien Launcher.exe
echo ============================================================
echo.

:: Prompt to run release.py
set /p choice="Do you want to release this version to GitHub? (y/N): "
if /i "%choice%"=="y" (
    echo.
    echo Launching release.py...
    python release.py
) else (
    echo Opening output directory...
    explorer dist
)

pause
