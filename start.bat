@echo off
echo Stopping containers...
docker-compose down

echo.
echo Rebuilding web container...
docker-compose build web

echo.
echo Starting containers...
docker-compose up -d

echo.
echo Waiting 15 seconds for containers to start...
timeout /t 15 /nobreak

echo.
echo Checking container status...
docker ps

echo.
echo.
echo Try accessing: http://localhost:8000
echo Admin panel: http://localhost:8000/admin
echo Study Agent: http://localhost:8000/study-agent/
echo.
pause

