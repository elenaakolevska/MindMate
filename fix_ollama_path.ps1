# Quick Fix: Додај Ollama во PATH
# Оваа скрипта ќе го пронајде Ollama и ќе го додаде во PATH

Write-Host "🔧 БРЗА ПОПРАВКА ЗА OLLAMA PATH" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Пронајди Ollama
Write-Host "Барам Ollama..." -ForegroundColor Yellow

$ollamaPath = $null
$possiblePaths = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "C:\Program Files\Ollama\ollama.exe",
    "C:\Program Files (x86)\Ollama\ollama.exe",
    "$env:ProgramFiles\Ollama\ollama.exe",
    "$env:USERPROFILE\AppData\Local\Programs\Ollama\ollama.exe"
)

foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $ollamaPath = $path
        Write-Host "✅ Пронајдов Ollama: $ollamaPath" -ForegroundColor Green
        break
    }
}

if (-not $ollamaPath) {
    Write-Host "❌ Ollama не е пронајден" -ForegroundColor Red
    Write-Host ""
    Write-Host "Дали сте сигурни дека е инсталиран?" -ForegroundColor Yellow
    Write-Host "Проверете во 'Add or Remove Programs' -> 'Ollama'" -ForegroundColor Cyan
    exit 1
}

$ollamaDir = Split-Path $ollamaPath -Parent
Write-Host "Ollama директориум: $ollamaDir" -ForegroundColor Gray
Write-Host ""

# Провери дали е веќе во PATH
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -like "*$ollamaDir*") {
    Write-Host "ℹ️  Ollama веќе е во USER PATH" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Можеби треба да го рестартирате PowerShell." -ForegroundColor Yellow
    Write-Host ""
    $restart = Read-Host "Дали да отворам нов PowerShell прозорец? (y/n)"
    if ($restart -eq "y" -or $restart -eq "Y") {
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'"
        Write-Host "✅ Нов PowerShell прозорец е отворен" -ForegroundColor Green
        Write-Host "Затворете го овој и користете го новиот." -ForegroundColor Yellow
    }
} else {
    Write-Host "Додавам Ollama во USER PATH..." -ForegroundColor Yellow

    try {
        # Додај во USER PATH
        $newPath = "$currentPath;$ollamaDir"
        [Environment]::SetEnvironmentVariable("Path", $newPath, "User")

        Write-Host "✅ Успешно! Ollama е додаден во PATH" -ForegroundColor Green
        Write-Host ""
        Write-Host "ВАЖНО: Промените ќе важат во нови PowerShell прозорци." -ForegroundColor Yellow
        Write-Host ""

        $restart = Read-Host "Дали да отворам нов PowerShell прозорец? (y/n)"
        if ($restart -eq "y" -or $restart -eq "Y") {
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; Write-Host 'Тестирајте со: ollama --version' -ForegroundColor Cyan"
            Write-Host ""
            Write-Host "✅ Нов PowerShell прозорец е отворен" -ForegroundColor Green
            Write-Host "Затворете го овој и користете го новиот." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "❌ Грешка: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Обидете се мануелно:" -ForegroundColor Yellow
        Write-Host "1. Отворете 'Environment Variables' (пребарувајте во Start)" -ForegroundColor Cyan
        Write-Host "2. Во 'User variables', најдете 'Path' и кликнете 'Edit'" -ForegroundColor Cyan
        Write-Host "3. Кликнете 'New' и додајте:" -ForegroundColor Cyan
        Write-Host "   $ollamaDir" -ForegroundColor White
        Write-Host "4. Кликнете OK и рестартирајте го PowerShell" -ForegroundColor Cyan
    }
}

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan

# За оваа сесија, додај во PATH
$env:Path = "$ollamaDir;$env:Path"
Write-Host ""
Write-Host "За оваа PowerShell сесија, Ollama е ПРИВРЕМЕНО додаден." -ForegroundColor Cyan
Write-Host "Тестирајте со: ollama --version" -ForegroundColor Yellow
Write-Host ""

