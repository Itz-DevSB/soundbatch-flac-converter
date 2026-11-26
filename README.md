# SoundBatch — Bulk Audio to FLAC

A Windows desktop app for converting folders of audio to FLAC with FFmpeg. It scans nested folders, accepts individual files, keeps folder structure, skips FLAC inputs and existing outputs, shows progress, and supports cancellation. It never deletes source files.

> Converting MP3, AAC, Opus, or another lossy format to FLAC does not restore sound details already lost. It stores the decoded audio in a lossless format without another lossy encode.

## Requirements

- Windows 10 or 11
- Python 3.10 or newer
- FFmpeg available on PATH

## Setup

1. Install Python from [python.org](https://www.python.org/downloads/) if needed.
2. In Windows Terminal or Command Prompt, run `winget install Gyan.FFmpeg`.
3. Reopen the terminal after FFmpeg installs.
4. Double-click `run_converter.bat`.

You can also start it with `python converter.py`. The app uses only Python's standard library; no pip packages are needed.

## Use

Add a folder or files, choose an output folder, and select **Convert to FLAC**. Folder scans preserve paths beneath the selected folder. Existing destination files are skipped. Cancel stops the current encode and removes its temporary output.

Supported extensions include MP3, AAC, M4A, MP4 audio, OGG, Opus, WMA, WAV, AIFF, ALAC, APE, WavPack, FLAC (skipped), MKA, M4B, CAF, AMR, AC-3, DTS, and TTA. Exact codec support depends on your FFmpeg build.

## Optional EXE

Install PyInstaller with `python -m pip install pyinstaller`, then run `pyinstaller --onefile --windowed --name SoundBatch converter.py`. FFmpeg still needs to be installed separately and on PATH.

