@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
.venv\Scripts\python.exe server.py
pause
exit /b 0
:failed
echo Setup failed. Install Python 3.11 or 3.12 64-bit, enable the Python launcher, and check internet access.
pause
exit /b 1
