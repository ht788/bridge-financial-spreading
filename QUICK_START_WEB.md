# Quick Start - Web UI

Get the Bridge Financial Spreader web interface running in 5 minutes.

## Prerequisites Check

```bash
# Check Python (need 3.10+)
python --version

# Check Node.js (need 18+)
node --version

# Check npm
npm --version
```

If any are missing, install them first.

## Step 1: Configure Environment

```bash
# Copy example environment file
cp env.example .env

# Edit .env and add your API keys
# Required: OPENAI_API_KEY
# Recommended: LANGSMITH_API_KEY
```

## Step 2: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt

# Install Node.js dependencies
cd frontend
npm install
cd ..
```

## Step 3: Start the Application

### Windows:
```bash
start.bat
```

### macOS/Linux:
```bash
chmod +x start.sh
./start.sh
```

### Or manually (two terminals):

**Terminal 1:**
```bash
python backend/main.py
```

**Terminal 2:**
```bash
cd frontend
npm run dev
```

## Step 4: Open in Browser

Navigate to: **http://localhost:5173**

## Step 5: Upload and Process

1. Drag and drop a PDF financial statement
2. Select document type (Income/Balance)
3. Click "Process Statement" (the fiscal period is auto-detected from the statement headers)
4. View results in beautiful side-by-side layout!

## Troubleshooting

### "Command not found: python"
Try `python3` instead of `python`

### "Module not found"
```bash
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

### "Port already in use"
Kill the process or change ports in `backend/main.py` and `frontend/vite.config.ts`

### "OPENAI_API_KEY not set"
Edit `.env` file and add your OpenAI API key

## Next Steps

- Read [WEB_UI_README.md](WEB_UI_README.md) for full documentation
- Try the example files in `example_financials/`
- Customize colors in `frontend/tailwind.config.js`
- Deploy to production (see WEB_UI_README.md)

## Example Usage

```bash
# Test with example files
1. Open http://localhost:5173
2. Upload: example_financials/FOMIN+LLC_Profit+and+Loss--.pdf
3. Document Type: Income Statement
4. Period: Latest
5. Click "Process Statement"
```

Enjoy! 🚀
