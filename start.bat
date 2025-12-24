@echo off
echo.
echo ========================================
echo   ?? READ RECEIPTS - STARTING SERVER
echo ========================================
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Navigate to app directory and start server
cd app
echo.
echo Starting server at http://localhost:8000
echo Press Ctrl+C to stop
echo.
python main.py
