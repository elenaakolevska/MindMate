# Ollama Setup Script за MindMate
# Автоматска инсталација и конфигурација

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "🚀 OLLAMA SETUP ЗА MINDMATE" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Чекор 1: Провери дали Ollama е инсталиран
Write-Host "📋 Чекор 1: Проверка на Ollama..." -ForegroundColor Yellow

$ollamaInstalled = Get-Command ollama -ErrorAction SilentlyContinue
$ollamaPath = $null

if ($ollamaInstalled) {
    Write-Host "✅ Ollama е веќе достапен во PATH!" -ForegroundColor Green
    $ollamaPath = $ollamaInstalled.Source
    $version = ollama --version
    Write-Host "   Верзија: $version" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Ollama не е пронајден во PATH" -ForegroundColor Yellow
    Write-Host "   Барам Ollama во стандардните локации..." -ForegroundColor Gray

    # Пребарувај во типични локации за инсталација
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
            Write-Host "   ✅ Пронајдов Ollama: $ollamaPath" -ForegroundColor Green
            break
        }
    }

    # Ако не е пронајден, пребарувај рекурзивно (побавно но погрундно)
    if (-not $ollamaPath) {
        Write-Host "   Пребарувам сè директориуми..." -ForegroundColor Gray
        $searchPaths = @("C:\Program Files", "C:\Program Files (x86)", "$env:LOCALAPPDATA\Programs")
        foreach ($searchPath in $searchPaths) {
            if (Test-Path $searchPath) {
                $found = Get-ChildItem -Path $searchPath -Filter "ollama.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($found) {
                    $ollamaPath = $found.FullName
                    Write-Host "   ✅ Пронајдов Ollama: $ollamaPath" -ForegroundColor Green
                    break
                }
            }
        }
    }

    if ($ollamaPath) {
        # Додај во PATH за оваа сесија
        $ollamaDir = Split-Path $ollamaPath -Parent
        $env:Path = "$ollamaDir;$env:Path"
        Write-Host "   ✅ Додадов Ollama во PATH за оваа сесија" -ForegroundColor Green

        # Предложи трајно додавање во PATH
        Write-Host ""
        Write-Host "   ВАЖНО: Ollama е пронајден но не е во PATH." -ForegroundColor Yellow
        Write-Host "   Препорака: Додајте го трајно во PATH:" -ForegroundColor Yellow
        Write-Host "   1. Отворете 'Environment Variables' (System Properties)" -ForegroundColor Cyan
        Write-Host "   2. Во 'User variables', најдете 'Path'" -ForegroundColor Cyan
        Write-Host "   3. Кликнете 'Edit' и додајте:" -ForegroundColor Cyan
        Write-Host "      $ollamaDir" -ForegroundColor White
        Write-Host ""
        $addPath = Read-Host "   Дали сакате да го додадам автоматски во USER PATH? (y/n)"

        if ($addPath -eq "y" -or $addPath -eq "Y") {
            try {
                $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
                if ($userPath -notlike "*$ollamaDir*") {
                    [Environment]::SetEnvironmentVariable("Path", "$userPath;$ollamaDir", "User")
                    Write-Host "   ✅ Ollama е додаден во USER PATH!" -ForegroundColor Green
                    Write-Host "   Рестартирајте го PowerShell за да влезе во сила." -ForegroundColor Yellow
                } else {
                    Write-Host "   ℹ️  Ollama веќе е во USER PATH" -ForegroundColor Cyan
                }
            } catch {
                Write-Host "   ❌ Грешка при додавање во PATH: $_" -ForegroundColor Red
            }
        }

        # Тестирај дали сега работи
        $testOllama = Get-Command ollama -ErrorAction SilentlyContinue
        if ($testOllama) {
            $version = ollama --version
            Write-Host "   ✅ Ollama сега работи! Верзија: $version" -ForegroundColor Green
        }
    } else {
        Write-Host "   ❌ Ollama не е пронајден" -ForegroundColor Red
        Write-Host ""
        Write-Host "Ве молиме инсталирајте го Ollama:" -ForegroundColor Yellow
        Write-Host "1. Посетете: https://ollama.com/download" -ForegroundColor Cyan
        Write-Host "2. Преземете 'OllamaSetup.exe'" -ForegroundColor Cyan
        Write-Host "3. Инсталирајте го (инсталацијата автоматски го додава во PATH)" -ForegroundColor Cyan
        Write-Host "4. Рестартирајте го PowerShell" -ForegroundColor Cyan
        Write-Host "5. Извршете ја оваа скрипта повторно" -ForegroundColor Cyan
        Write-Host ""

        # Понуди автоматска инсталација со winget
        $hasWinget = Get-Command winget -ErrorAction SilentlyContinue
        if ($hasWinget) {
            Write-Host "Или инсталирајте автоматски со winget:" -ForegroundColor Yellow
            Write-Host "  winget install Ollama.Ollama" -ForegroundColor Cyan
            Write-Host ""
            $install = Read-Host "Дали сакате да инсталирате со winget сега? (y/n)"
            if ($install -eq "y" -or $install -eq "Y") {
                Write-Host "Инсталирам Ollama..." -ForegroundColor Yellow
                winget install Ollama.Ollama
                Write-Host "✅ Инсталацијата заврши! Рестартирајте го PowerShell." -ForegroundColor Green
            }
        }

        exit 1
    }
}

Write-Host ""

# Чекор 2: Провери дали Ollama серvisот работи
Write-Host "📋 Чекор 2: Проверка дали Ollama работи..." -ForegroundColor Yellow

$ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue

if ($ollamaProcess) {
    Write-Host "✅ Ollama серvisот работи!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Ollama серvisот не работи" -ForegroundColor Yellow
    Write-Host "   Стартувам Ollama..." -ForegroundColor Gray

    # Стартувај Ollama во позадина
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3

    $ollamaProcess = Get-Process ollama -ErrorAction SilentlyContinue
    if ($ollamaProcess) {
        Write-Host "✅ Ollama успешно стартуван!" -ForegroundColor Green
    } else {
        Write-Host "❌ Не можев да го стартувам Ollama" -ForegroundColor Red
        Write-Host "   Обидете се мануелно: ollama serve" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""

# Чекор 3: Провери достапни модели
Write-Host "📋 Чекор 3: Проверка на инсталирани модели..." -ForegroundColor Yellow

$models = ollama list 2>&1
if ($models -match "llama3") {
    Write-Host "✅ Llama3 моделот е веќе превлечен!" -ForegroundColor Green
    Write-Host "$models" -ForegroundColor Gray
} else {
    Write-Host "⚠️  Llama3 моделот не е превлечен" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Llama3 е околу 4.7GB. Ова може да трае неколку минути." -ForegroundColor Gray
    $pull = Read-Host "Дали сакате да го превлечете сега? (y/n)"

    if ($pull -eq "y" -or $pull -eq "Y") {
        Write-Host "Превлекувам Llama3 модел..." -ForegroundColor Yellow
        Write-Host "(Ова може да трае 5-15 минути зависно од вашата интернет врска)" -ForegroundColor Gray

        ollama pull llama3

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Llama3 успешно превлечен!" -ForegroundColor Green
        } else {
            Write-Host "❌ Грешка при превлекување на Llama3" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "⚠️  Прескокнувам превлекување. Ќе треба да го направите мануелно:" -ForegroundColor Yellow
        Write-Host "   ollama pull llama3" -ForegroundColor Cyan
    }
}

Write-Host ""

# Чекор 4: Тестирај модел
Write-Host "📋 Чекор 4: Тестирање на модел..." -ForegroundColor Yellow

$testResponse = ollama run llama3 "Respond with just 'OK' if you understand" --verbose $false 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Моделот работи!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Тестот не помина целосно, но моделот можеби сепак работи" -ForegroundColor Yellow
}

Write-Host ""

# Чекор 5: Провери Python environment
Write-Host "📋 Чекор 5: Проверка на Python окружување..." -ForegroundColor Yellow

$pythonPath = Get-Command python -ErrorAction SilentlyContinue

if ($pythonPath) {
    Write-Host "✅ Python е достапен" -ForegroundColor Green

    # Провери дали е во virtual environment
    if ($env:VIRTUAL_ENV) {
        Write-Host "✅ Virtual environment е активен: $env:VIRTUAL_ENV" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Virtual environment не е активен" -ForegroundColor Yellow
        Write-Host "   Активирајте го со: .\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    }

    # Провери дали ollama пакетот е инсталиран
    $ollamaPkg = pip list 2>&1 | Select-String "ollama"
    if ($ollamaPkg) {
        Write-Host "✅ ollama Python пакет е инсталиран" -ForegroundColor Green
    } else {
        Write-Host "⚠️  ollama Python пакет не е инсталиран" -ForegroundColor Yellow
        $installPip = Read-Host "Дали сакате да го инсталирате сега? (y/n)"

        if ($installPip -eq "y" -or $installPip -eq "Y") {
            Write-Host "Инсталирам Python пакети..." -ForegroundColor Yellow
            pip install ollama langchain langgraph langchain-community langchain-core
            Write-Host "✅ Пакетите се инсталирани!" -ForegroundColor Green
        }
    }
} else {
    Write-Host "❌ Python не е пронајден" -ForegroundColor Red
    Write-Host "   Инсталирајте Python 3.10+ од python.org" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "🎯 РЕЗИМЕ / SUMMARY" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Финална проверка
$allGood = $true

if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host "✅ Ollama инсталиран" -ForegroundColor Green
} else {
    Write-Host "❌ Ollama НЕ е инсталиран" -ForegroundColor Red
    $allGood = $false
}

if (Get-Process ollama -ErrorAction SilentlyContinue) {
    Write-Host "✅ Ollama сервис работи" -ForegroundColor Green
} else {
    Write-Host "❌ Ollama сервис НЕ работи" -ForegroundColor Red
    $allGood = $false
}

$modelsCheck = ollama list 2>&1
if ($modelsCheck -match "llama3") {
    Write-Host "✅ Llama3 модел е достапен" -ForegroundColor Green
} else {
    Write-Host "❌ Llama3 модел НЕ е достапен" -ForegroundColor Red
    $allGood = $false
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "✅ Python е достапен" -ForegroundColor Green
} else {
    Write-Host "❌ Python НЕ е достапен" -ForegroundColor Red
    $allGood = $false
}

Write-Host ""

if ($allGood) {
    Write-Host "🎉 СЕ Е ГОТОВО! / ALL SET!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Следни чекори:" -ForegroundColor Yellow
    Write-Host "1. Активирајте го virtual environment:" -ForegroundColor Cyan
    Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Тестирајте ги MindMate тестовите:" -ForegroundColor Cyan
    Write-Host "   python test_macedonian_support.py" -ForegroundColor Gray
    Write-Host ""
    Write-Host "3. Ако сите тестови поминат, започнете со развој! 🚀" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  НЕКОИ РАБОТИ ТРЕБА ДА СЕ ПОПРАВАТ" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Погледнете го OLLAMA_SETUP_GUIDE.md за детали" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "За повеќе помош, видете: OLLAMA_SETUP_GUIDE.md" -ForegroundColor Gray
Write-Host ""

