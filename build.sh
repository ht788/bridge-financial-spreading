#!/usr/bin/env bash
# Render build script

set -e  # Exit on error
set -o pipefail  # Exit on pipe failures

echo "====================================="
echo "Building Bridge Financial Spreader"
echo "====================================="

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip

# Use combined requirements file for Render
if [ -f "requirements-render.txt" ]; then
    echo "Installing from requirements-render.txt (combined)..."
    pip install -r requirements-render.txt
else
    echo "Installing from separate requirements files..."
    pip install -r requirements.txt
    pip install -r backend/requirements.txt
fi

# Verify critical packages
echo "Verifying installations..."
python -c "import uvicorn; print(f'✓ uvicorn {uvicorn.__version__}')" || { echo "✗ ERROR: uvicorn not installed!"; exit 1; }
python -c "import fastapi; print(f'✓ fastapi {fastapi.__version__}')" || { echo "✗ ERROR: fastapi not installed!"; exit 1; }
python -c "import anthropic; print(f'✓ anthropic {anthropic.__version__}')" || echo "⚠ WARNING: anthropic not installed (optional)"
python -c "import openai; print(f'✓ openai {openai.__version__}')" || echo "⚠ WARNING: openai not installed (optional)"

# Install Node dependencies and build frontend
echo "Checking if frontend directory exists..."
if [ ! -d "frontend" ]; then
    echo "✗ ERROR: frontend directory not found!"
    exit 1
fi

echo "Installing Node dependencies..."
cd frontend

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "✗ ERROR: package.json not found in frontend directory!"
    exit 1
fi

# Use npm ci for faster, more reliable installs in CI/CD
npm ci --prefer-offline --no-audit || { echo "✗ ERROR: npm ci failed!"; exit 1; }

echo "Building frontend..."
npm run build || { echo "✗ ERROR: Frontend build failed!"; exit 1; }

# Verify build output
if [ -d "dist" ]; then
    echo "✓ Frontend built successfully"
    echo "Build output:"
    ls -lh dist/
    
    # Verify index.html exists
    if [ ! -f "dist/index.html" ]; then
        echo "✗ ERROR: dist/index.html not found!"
        exit 1
    fi
    
    # Verify assets directory exists
    if [ ! -d "dist/assets" ]; then
        echo "⚠ WARNING: dist/assets directory not found (may be OK if no assets)"
    fi
else
    echo "✗ ERROR: Frontend dist folder not found!"
    exit 1
fi

cd ..

echo "====================================="
echo "Build complete!"
echo "====================================="
echo "✓ Python dependencies installed"
echo "✓ Frontend built and verified"
echo "Ready for deployment"
