#!/usr/bin/env bash
# Render build script

set -e  # Exit on error

echo "====================================="
echo "Building Bridge Financial Spreader"
echo "====================================="

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Install Node dependencies and build frontend
echo "Installing Node dependencies..."
cd frontend
npm ci --prefer-offline --no-audit

echo "Building frontend..."
npm run build

cd ..

echo "====================================="
echo "Build complete!"
echo "====================================="
