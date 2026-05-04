@echo off
setlocal EnableDelayedExpansion
title Thumb Pipeline - Build Release

echo.
echo ================================================
echo   Thumb Pipeline -- Build Release
echo ================================================
echo.

:: Check project root
if not exist "backend\main.py" (
    echo [ERROR] Run this script from the project root ^(Colab/^)
    exit /b 1
)

:: Step 0: Check ffmpeg
echo [0/5] Checking ffmpeg...
if not exist "tools\ffmpeg.exe" (
    echo [ERROR] tools\ffmpeg.exe not found.
    echo Download: https://www.gyan.dev/ffmpeg/builds/
    echo Get ffmpeg-release-essentials.zip, extract ffmpeg.exe + ffprobe.exe into tools\
    exit /b 1
)
if not exist "tools\ffprobe.exe" (
    echo [ERROR] tools\ffprobe.exe not found. See above.
    exit /b 1
)
echo       OK - ffmpeg + ffprobe found

:: Step 1: Activate venv
echo.
echo [1/5] Activating Python virtual environment...
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] .venv not found. Run: python -m venv .venv
    exit /b 1
)
call .venv\Scripts\activate.bat

:: Step 2: Install PyInstaller
echo.
echo [2/5] Installing PyInstaller...
pip install pyinstaller --default-timeout=1000
if errorlevel 1 (
    echo [ERROR] pip install pyinstaller failed
    exit /b 1
)

:: Step 3: Build backend_server.exe
echo.
echo [3/5] Building backend_server.exe with PyInstaller...
echo       (First run may take 2-5 minutes)
if exist "dist\backend_server" rmdir /s /q "dist\backend_server"
pyinstaller backend_server.spec --noconfirm
if errorlevel 1 (
    echo [ERROR] PyInstaller failed
    exit /b 1
)
echo       OK - dist\backend_server\backend_server.exe

:: Step 4: Tauri build
echo.
echo [4/5] Building Tauri desktop app...
echo       (First Rust compile may take 5-10 minutes)
npm run build
if errorlevel 1 (
    echo [ERROR] Tauri build failed
    exit /b 1
)

:: Step 5: Copy backend bundle next to Tauri exe
echo.
echo [5/5] Packaging release...
set TAURI_RELEASE=src-tauri\target\release
set DEST=%TAURI_RELEASE%\_internal

if exist "%DEST%" rmdir /s /q "%DEST%"
mkdir "%DEST%"
copy /y "dist\backend_server.exe" "%DEST%\" >nul
if errorlevel 1 (
    echo [ERROR] Copy backend failed
    exit /b 1
)

:: Copy required binaries and secrets
echo Copying ffmpeg and secrets into %DEST%...
copy /y "tools\ffmpeg.exe" "%DEST%\" >nul
copy /y "tools\ffprobe.exe" "%DEST%\" >nul
copy /y "client_secrets.json" "%DEST%\" >nul

echo.
echo ================================================
echo   BUILD SUCCESSFUL!
echo ================================================
echo.
echo Distribution folder: %TAURI_RELEASE%\
echo   Thumb Pipeline Desktop.exe   ^<-- main executable
echo   _internal\                   ^<-- Python backend (do not delete)
echo     backend_server.exe
echo     client_secrets.json
echo     ffmpeg.exe
echo     ffprobe.exe
echo.
echo Users only need to copy the entire %TAURI_RELEASE%\ folder and run the exe.
echo.
