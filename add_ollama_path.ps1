# Add Ollama to PATH for current PowerShell session
# Додај Ollama во PATH за тековната PowerShell сесија
#
# Usage / Користење:
#   . .\add_ollama_path.ps1
#   (Note the dot and space at the beginning!)

$ollamaDir = "C:\Users\elen4\AppData\Local\Programs\Ollama"

if ($env:Path -notlike "*$ollamaDir*") {
    $env:Path = "$ollamaDir;$env:Path"
    Write-Host "✅ Ollama додаден во PATH за оваа сесија" -ForegroundColor Green
    Write-Host "   Локација: $ollamaDir" -ForegroundColor Gray
} else {
    Write-Host "ℹ️  Ollama веќе е во PATH" -ForegroundColor Cyan
}

# Quick test
$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    $version = ollama --version 2>&1
    Write-Host "✅ Ollama работи: $version" -ForegroundColor Green
} else {
    Write-Host "⚠️  Ollama не може да се пронајде" -ForegroundColor Yellow
}

