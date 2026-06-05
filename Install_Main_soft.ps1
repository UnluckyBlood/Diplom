# Install_Main_soft.ps1
# Запуск: правой кнопкой -> Запуск от имени администратора
# или в консоли: powershell -ExecutionPolicy Bypass -File Install_Main_soft.ps1

param([switch]$Force)

# Проверка прав администратора
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Запустите PowerShell от имени администратора!" -ForegroundColor Red
    Write-Host "Нажмите правой кнопкой по файлу -> Запуск от имени администратора" -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

Set-Location $PSScriptRoot
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "    УСТАНОВКА ПРОМ МОНИТОРИНГА" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# --- Функция проверки реального Python ---
function Test-RealPython {
    try {
        $py = Get-Command python -ErrorAction Stop
        if ($py.Source -like "*WindowsApps*") { return $false }
        $ver = & python --version 2>&1
        if ($ver -match "3\.11") { return $true }
    } catch {}
    return $false
}

# --- 1. Python ---
Write-Host "[1/6] Проверка Python..." -ForegroundColor Yellow
if (Test-RealPython -and -not $Force) {
    Write-Host "? Python 3.11 уже установлен" -ForegroundColor Green
} else {
    Write-Host "?? Установка Python 3.11..." -ForegroundColor Yellow
    $url = "https://www.python.org/ftp/python/3.11.8/python-3.11.8-amd64.exe"
    $installer = "$env:TEMP\python-3.11.8-amd64.exe"
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Start-Process -Wait -FilePath $installer -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"
    Remove-Item $installer -Force
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "? Python установлен" -ForegroundColor Green
}

# --- 2. Ollama ---
Write-Host "[2/6] Проверка Ollama..." -ForegroundColor Yellow
$ollamaFound = $false
$ollamaExe = $null
$cmdOllama = Get-Command ollama -ErrorAction SilentlyContinue
if ($cmdOllama -and (Test-Path $cmdOllama.Source)) {
    $ollamaFound = $true
    $ollamaExe = $cmdOllama.Source
    Write-Host "? Ollama найден в PATH: $ollamaExe" -ForegroundColor Green
}
if (-not $ollamaFound -and (Test-Path "C:\Program Files\Ollama\ollama.exe")) {
    $ollamaFound = $true
    $ollamaExe = "C:\Program Files\Ollama\ollama.exe"
    Write-Host "? Ollama найден по стандартному пути" -ForegroundColor Green
}
if ($ollamaFound -and -not $Force) {
    Write-Host "? Ollama уже установлен. Пропускаем установку." -ForegroundColor Green
} else {
    Write-Host "?? Установка Ollama..." -ForegroundColor Yellow
    $url = "https://ollama.com/download/OllamaSetup.exe"
    $installer = "$env:TEMP\OllamaSetup.exe"
    Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing
    Start-Process -Wait -FilePath $installer -ArgumentList "/S"
    Remove-Item $installer -Force
    $ollamaExe = "C:\Program Files\Ollama\ollama.exe"
    Write-Host "? Ollama установлен" -ForegroundColor Green
}
if ($ollamaExe) {
    $ollamaDir = Split-Path $ollamaExe
    $env:Path = "$ollamaDir;$env:Path"
}

# --- 3. Запуск сервера Ollama ---
Write-Host "[3/6] Запуск сервера Ollama..." -ForegroundColor Yellow
$ollamaProc = Get-Process ollama -ErrorAction SilentlyContinue
if ($ollamaProc) {
    Write-Host "? Ollama уже запущен" -ForegroundColor Green
} else {
    if (-not $ollamaExe -or -not (Test-Path $ollamaExe)) {
        Write-Host "? Не удалось найти ollama.exe. Установите вручную." -ForegroundColor Red
        Read-Host "Нажмите Enter"
        exit 1
    }
    Start-Process $ollamaExe -ArgumentList "serve" -WindowStyle Hidden
    Write-Host "? Ожидание запуска сервера (5 сек)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    Write-Host "? Сервер Ollama запущен" -ForegroundColor Green
}

# --- 4. Модель Mistral ---
Write-Host "[4/6] Проверка модели Mistral 7B..." -ForegroundColor Yellow
if (-not $ollamaExe) {
    Write-Host "? Ollama не найден. Невозможно проверить модель." -ForegroundColor Red
    Read-Host "Нажмите Enter"
    exit 1
}
$models = & "$ollamaExe" list
if ($models -like "*mistral*") {
    Write-Host "? Модель Mistral 7B уже загружена" -ForegroundColor Green
} else {
    Write-Host "?? Загрузка модели Mistral 7B (около 4 ГБ, 10-20 минут)..." -ForegroundColor Yellow
    Write-Host "?? НЕ ЗАКРЫВАЙТЕ ОКНО до завершения!" -ForegroundColor Red
    & "$ollamaExe" pull mistral
    if ($LASTEXITCODE -ne 0) {
        Write-Host "? Ошибка загрузки модели. Попробуйте вручную: ollama pull mistral" -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
    Write-Host "? Модель Mistral 7B загружена" -ForegroundColor Green
}

# --- 5. Виртуальное окружение и зависимости ---
Write-Host "[5/6] Настройка окружения Python..." -ForegroundColor Yellow
if (-not (Test-Path "venv\Scripts\python.exe")) {
    python -m venv venv
}
Write-Host "Обновление pip..." -ForegroundColor Yellow
.\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
Write-Host "Установка зависимостей..." -ForegroundColor Yellow
if (Test-Path "requirements.txt") {
    .\venv\Scripts\python.exe -m pip install -r requirements.txt --quiet
} else {
    .\venv\Scripts\python.exe -m pip install --quiet fastapi uvicorn[standard] pyserial requests numpy python-multipart PyJWT PyPDF2 reportlab
}
Write-Host "? Зависимости установлены" -ForegroundColor Green

# --- 6. Запуск через Windows Terminal (только DataProcessor и WebServer) ---
Write-Host "[6/6] Запуск приложения..." -ForegroundColor Yellow
$venvPython = Resolve-Path "venv\Scripts\python.exe"
$dpScript = Resolve-Path "DataProcessor\main.py"
$wsScript = Resolve-Path "WebServer\webserver.py"

$wtExe = (Get-Command wt -ErrorAction SilentlyContinue).Source
if (-not $wtExe) {
    Write-Host "?? Windows Terminal не найден. Установка через winget..." -ForegroundColor Yellow
    winget install Microsoft.WindowsTerminal --accept-package-agreements --silent
    $wtExe = (Get-Command wt -ErrorAction SilentlyContinue).Source
    if (-not $wtExe) {
        Write-Host "? Не удалось установить Windows Terminal. Установите вручную из Microsoft Store." -ForegroundColor Red
        Read-Host "Нажмите Enter"
        exit 1
    }
}

# Запускаем только две вкладки (Ollama уже работает в фоне)
$wtArgs = @(
    "-w", "0",
    "nt", "--title", "DataProcessor", $venvPython, $dpScript,
    ";",
    "nt", "--title", "WebServer", $venvPython, $wsScript
)

Write-Host "Запуск Windows Terminal с двумя вкладками (Ollama уже работает в фоне)..." -ForegroundColor Yellow
& $wtExe $wtArgs

Start-Sleep -Seconds 5
Start-Process "http://localhost:8000"