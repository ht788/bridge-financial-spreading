@echo off
REM Startup script for Bridge Financial Spreader Web UI (Windows)

echo ====================================
echo Bridge Financial Spreader
echo ====================================
echo.
echo Starting backend startup service...
start "Backend Startup Service" cmd /k "node backend_startup_service.js"

echo Waiting for startup service to initialize...
timeout /t 2 /nobreak >nul

echo Starting backend server...
start "Backend Server" cmd /k "python backend/main.py"

echo Waiting for backend to initialize...
timeout /t 3 /nobreak >nul

echo Starting frontend development server...
start "Frontend Server" cmd /k "cd frontend && npm run dev"

echo.
echo ====================================
echo Servers starting...
echo ====================================
echo Startup Service: http://localhost:8001
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Press Ctrl+C in each window to stop servers
echo ====================================
