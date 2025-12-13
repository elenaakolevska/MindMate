# Fix and start MindMate containers
Write-Host "Stopping all containers..." -ForegroundColor Yellow
docker-compose down

Write-Host "`nCleaning migration cache..." -ForegroundColor Yellow
Remove-Item ".\MindMateAPP\migrations\__pycache__" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "`nRebuilding web container..." -ForegroundColor Yellow
docker-compose build web

Write-Host "`nStarting containers..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "`nWaiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "`nChecking container status..." -ForegroundColor Cyan
$webStatus = docker ps --filter "name=mindmate-web" --format "{{.Status}}"
$dbStatus = docker ps --filter "name=mindmate-db" --format "{{.Status}}"

if ($webStatus -match "Up") {
    Write-Host "✓ Web container: $webStatus" -ForegroundColor Green
} else {
    Write-Host "✗ Web container is not running!" -ForegroundColor Red
    Write-Host "`nShowing web container logs:" -ForegroundColor Yellow
    docker logs mindmate-web-1 --tail 50
    exit 1
}

if ($dbStatus -match "Up") {
    Write-Host "✓ DB container: $dbStatus" -ForegroundColor Green
} else {
    Write-Host "✗ DB container is not running!" -ForegroundColor Red
    exit 1
}

Write-Host "`n✓ All containers are running!" -ForegroundColor Green
Write-Host "`nAccess your application at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Access admin panel at: http://localhost:8000/admin" -ForegroundColor Cyan
Write-Host "Access study agent at: http://localhost:8000/study-agent/" -ForegroundColor Cyan

