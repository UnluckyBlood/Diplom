Write-Host "🚀 Arduino Monitoring System Launcher" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit
}

# Check virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate venv
$venvPython = "venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Write-Host "✅ Virtual environment ready" -ForegroundColor Green
} else {
    Write-Host "❌ Virtual environment not created properly" -ForegroundColor Red
}

Write-Host "`n📦 Installing dependencies..." -ForegroundColor Yellow
& $venvPython -m pip install fastapi uvicorn pyserial requests websockets --quiet

Write-Host "`n🚀 Starting components..." -ForegroundColor Green
Write-Host "   Web Server: http://localhost:8000" -ForegroundColor Cyan

# Start web server
Start-Process -FilePath $venvPython -ArgumentList "WebServer\webserver.py" -WindowStyle Normal

Start-Sleep -Seconds 3

Write-Host "   Data Processor: COM3" -ForegroundColor Cyan

# Start data processor
Start-Process -FilePath $venvPython -ArgumentList "DataProcessor\simple_main.py" -WindowStyle Normal

Start-Sleep -Seconds 2

Write-Host "`n✅ System started!" -ForegroundColor Green
Write-Host "`n🌐 Open in browser: http://localhost:8000" -ForegroundColor Yellow
Write-Host "🛑 To stop: Close both command windows" -ForegroundColor Yellow

# Open browser
Start-Process "http://localhost:8000"

Write-Host "`nPress Enter to close this window..." -ForegroundColor Gray
Read-Host
