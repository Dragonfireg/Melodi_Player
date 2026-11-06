@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title Build Melodi Player - EXE

REM ============================================================
REM  Build Melodi Player menjadi .exe (PyInstaller)
REM  Letakkan file ini sejajar dengan:
REM    - melodi_player.py
REM    - melodi.ico
REM  Lalu jalankan dengan klik dua kali.
REM ============================================================

cd /d "%~dp0"

set "APP_NAME=Melodi"
set "APP_SCRIPT=melodi_player.py"
set "APP_ICON=melodi.ico"

echo.
echo ==========================================
echo   Build %APP_NAME% Player
echo ==========================================
echo.

REM --- 1. Cek file yang dibutuhkan ---
if not exist "%APP_SCRIPT%" (
    echo [ERROR] File %APP_SCRIPT% tidak ditemukan di folder ini.
    goto :fail
)
if not exist "%APP_ICON%" (
    echo [ERROR] File %APP_ICON% tidak ditemukan di folder ini.
    goto :fail
)

REM --- 2. Cek Python ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python tidak ditemukan. Install Python 3.10+ dan centang "Add to PATH".
    goto :fail
)
echo [OK] Python: 
%PY% --version

REM --- 3. Install dependensi ---
echo.
echo [1/4] Memasang dependensi...
%PY% -m pip install --upgrade pip >nul
%PY% -m pip install --upgrade pyinstaller PySide6 ytmusicapi yt-dlp
if errorlevel 1 (
    echo [ERROR] Gagal memasang dependensi. Periksa koneksi internet.
    goto :fail
)

REM --- 4. Bersihkan build lama ---
echo.
echo [2/4] Membersihkan build lama...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%APP_NAME%.spec" del /q "%APP_NAME%.spec"

REM --- 5. Build ---
REM  --onefile      : hasil satu file .exe
REM  --windowed     : tanpa jendela console
REM  --icon         : ikon file .exe (melodi.ico, multi-ukuran)
REM  --add-data     : sertakan melodi.ico di dalam paket
REM  --collect-all  : sertakan data/modul yt_dlp & ytmusicapi (import dinamis)
echo.
echo [3/4] Membangun EXE (bisa beberapa menit)...
%PY% -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --windowed ^
    --name "%APP_NAME%" ^
    --icon "%APP_ICON%" ^
    --add-data "%APP_ICON%;." ^
    --collect-all yt_dlp ^
    --collect-all ytmusicapi ^
    --hidden-import PySide6.QtMultimedia ^
    --exclude-module tkinter ^
    "%APP_SCRIPT%"
if errorlevel 1 (
    echo.
    echo [ERROR] Build gagal. Lihat pesan di atas.
    goto :fail
)

REM --- 6. Selesai ---
echo.
echo [4/4] Selesai!
if exist "dist\%APP_NAME%.exe" (
    echo.
    echo   Hasil: %~dp0dist\%APP_NAME%.exe
    echo.
    echo   Catatan: bila ikon .exe belum berubah di Explorer, itu cache ikon Windows.
    echo   Jalankan:  ie4uinit.exe -show   atau restart Explorer / pindahkan file .exe.
    explorer "dist"
) else (
    echo [ERROR] File dist\%APP_NAME%.exe tidak ditemukan.
    goto :fail
)

echo.
pause
exit /b 0

:fail
echo.
pause
exit /b 1
