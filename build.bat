@echo off
REM Build script for Hardware Diagnostic Tool
REM Creates standalone executable using PyInstaller

echo ========================================
echo Hardware Diagnostic Tool - Build Script
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

echo [1/5] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/5] Ensuring PyInstaller is installed...
pip install pyinstaller>=6.0.0
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)

echo.
echo [3/5] Cleaning previous build...
if exist "build" rmdir /S /Q "build"
if exist "dist" rmdir /S /Q "dist"
if exist "*.spec" del /Q "*.spec"

echo.
echo [4/5] Building executable (this may take several minutes)...
pyinstaller --name="HardwareDiagnosticTool" ^
    --onedir ^
    --windowed ^
    --clean ^
    --add-data="data;data" ^
    --add-data="assets;assets" ^
    --hidden-import=wmi ^
    --hidden-import=psutil ^
    --hidden-import=cpuinfo ^
    --hidden-import=GPUtil ^
    --hidden-import=pynvml ^
    --hidden-import=google.generativeai ^
    --hidden-import=customtkinter ^
    --hidden-import=PIL._tkinter_finder ^
    --collect-all=customtkinter ^
    --collect-submodules=google.generativeai ^
    --noconfirm ^
    main.py

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [5/5] Copying external tools to dist folder...
if not exist "dist\HardwareDiagnosticTool\data" mkdir "dist\HardwareDiagnosticTool\data"
if not exist "dist\HardwareDiagnosticTool\assets" mkdir "dist\HardwareDiagnosticTool\assets"
if not exist "dist\HardwareDiagnosticTool\logs" mkdir "dist\HardwareDiagnosticTool\logs"
if not exist "dist\HardwareDiagnosticTool\hwinfo" mkdir "dist\HardwareDiagnosticTool\hwinfo"
if not exist "dist\HardwareDiagnosticTool\Novabench" mkdir "dist\HardwareDiagnosticTool\Novabench"

REM Copy data and assets if they exist
if exist "data\*" xcopy /E /I /Y "data\*" "dist\HardwareDiagnosticTool\data\"
if exist "assets\*" xcopy /E /I /Y "assets\*" "dist\HardwareDiagnosticTool\assets\"

REM Copy external tools
if exist "hwinfo\*" xcopy /E /I /Y "hwinfo\*" "dist\HardwareDiagnosticTool\hwinfo\"
if exist "Novabench\*" xcopy /E /I /Y "Novabench\*" "dist\HardwareDiagnosticTool\Novabench\"

echo.
echo ========================================
echo [5/5] Cleaning up build artifacts...
if exist "build" rmdir /S /Q "build"
echo ========================================
echo.
echo Build completed successfully!
echo.
echo IMPORTANT: Always run the application from the 'dist' folder:
echo dist\HardwareDiagnosticTool\HardwareDiagnosticTool.exe
echo.
echo Note: Do NOT try to run any files inside the 'build' folder (it has been cleaned anyway).
echo.
pause
