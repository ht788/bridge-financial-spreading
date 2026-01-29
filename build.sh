#!/usr/bin/env bash
# Render build script

set -e  # Exit on error

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
python -c "import uvicorn; print(f'✓ uvicorn {uvicorn.__version__}')"
python -c "import fastapi; print(f'✓ fastapi {fastapi.__version__}')"
python -c "import anthropic; print(f'✓ anthropic {anthropic.__version__}')"

# Install Node dependencies and build frontend
echo "Installing Node dependencies..."
cd frontend
npm ci --prefer-offline --no-audit

echo "Building frontend..."
npm run build

# Verify build output
if [ -d "dist" ]; then
    echo "✓ Frontend built successfully"
    ls -lh dist/
else
    echo "✗ ERROR: Frontend dist folder not found!"
    exit 1
fi

cd ..

echo "====================================="
echo "Build complete!"
echo "====================================="
