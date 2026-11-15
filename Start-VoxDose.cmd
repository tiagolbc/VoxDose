@echo off
cd /d "%~dp0"
if exist "VoxDose-2.0.exe" (
    start "" "%~dp0VoxDose-2.0.exe"
    exit /b
)
if exist "dist\VoxDose-2.0.exe" (
    start "" "%~dp0dist\VoxDose-2.0.exe"
    exit /b
)
echo VoxDose-2.0.exe not found. / Arquivo VoxDose-2.0.exe nao encontrado.
echo Use the complete single-file release. Python is not required.
pause
