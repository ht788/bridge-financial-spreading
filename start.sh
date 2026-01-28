#!/bin/bash
# Startup script for Bridge Financial Spreader Web UI (macOS/Linux)

echo "===================================="
echo "Bridge Financial Spreader"
echo "===================================="
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping servers..."
    kill $STARTUP_SERVICE_PID 2>/dev/null
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on Ctrl+C
trap cleanup SIGINT SIGTERM

# Start backend startup service
echo "Starting backend startup service..."
node backend_startup_service.js &
STARTUP_SERVICE_PID=$!

# Wait for startup service to initialize
sleep 2

# Start backend
echo "Starting backend server..."
python backend/main.py &
BACKEND_PID=$!

# Wait for backend to initialize
sleep 3

# Start frontend
echo "Starting frontend development server..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "===================================="
echo "Servers running..."
echo "===================================="
echo "Startup Service: http://localhost:8001"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "===================================="

# Wait for either process to exit
wait
