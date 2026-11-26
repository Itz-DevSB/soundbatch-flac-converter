@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.10 or newer was not found. Install Python and try again.
  pause
  exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg was not found. Install it with: winget install Gyan.FFmpeg
  pause
  exit /b 1
)
python converter.py
if errorlevel 1 pause

