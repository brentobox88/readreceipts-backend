Write-Host "
========================================" -ForegroundColor Cyan
Write-Host "  🚀 READ RECEIPTS - STARTING SERVER" -ForegroundColor Cyan
Write-Host "========================================
" -ForegroundColor Cyan

# Activate virtual environment
if (Test-Path "venv\Scripts\activate.bat") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    cmd /c "call venv\Scripts\activate.bat"
}

Write-Host "
Starting server..." -ForegroundColor Yellow
Write-Host "🌐 Server: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📚 Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "
Press Ctrl+C to stop
" -ForegroundColor Gray

# Start the server
cd app
python main.py
