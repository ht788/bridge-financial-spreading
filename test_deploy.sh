#!/bin/bash
# Test deployment build process locally

echo "====================================="
echo "Testing Render Deployment Build"
echo "====================================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
python --version

# Install backend dependencies
echo ""
echo "✓ Installing Python dependencies..."
pip install -q -r requirements.txt
pip install -q -r backend/requirements.txt

# Check Node version
echo ""
echo "✓ Checking Node version..."
node --version
npm --version

# Install frontend dependencies
echo ""
echo "✓ Installing frontend dependencies..."
cd frontend
npm install

# Build frontend
echo ""
echo "✓ Building frontend..."
npm run build

# Check if dist folder was created
if [ -d "dist" ]; then
    echo ""
    echo "✅ Build successful! Frontend dist folder created."
    echo "   Files in dist/:"
    ls -lh dist/
else
    echo ""
    echo "❌ Build failed! No dist folder found."
    exit 1
fi

cd ..

echo ""
echo "====================================="
echo "✅ All checks passed!"
echo "====================================="
echo ""
echo "Ready to deploy to Render.com"
echo ""
echo "Next steps:"
echo "1. git add ."
echo "2. git commit -m 'Add Render deployment'"
echo "3. git push origin master"
echo "4. Go to render.com and create a new web service"
