# Bridge Financial Spreader - Web UI

A modern, production-ready web application for spreading financial statements with AI-powered extraction and beautiful visualization.

## 🎨 Features

- **Drag-and-Drop Upload**: Easy PDF upload with visual feedback
- **Side-by-Side View**: Compare original PDF with extracted data
- **Real-Time Processing**: See your financials extracted in seconds
- **Confidence Indicators**: Color-coded confidence scores for each field
- **Interactive Tooltips**: View source text and extraction details
- **Export Options**: Download as JSON or CSV
- **Responsive Design**: Beautiful UI built with TailwindCSS

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React Frontend                      │
│              (TypeScript + Vite)                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │   Upload    │  │ PDF Viewer  │  │   Tables    │ │
│  │   Page      │  │             │  │             │ │
│  └─────────────┘  └─────────────┘  └─────────────┘ │
└────────────────────┬────────────────────────────────┘
                     │ HTTP/REST
┌────────────────────┴────────────────────────────────┐
│                 FastAPI Backend                      │
│  ┌──────────────────────────────────────────────┐   │
│  │         Spreader Engine (spreader.py)        │   │
│  │     LangSmith + OpenAI Vision Models         │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** (for backend)
- **Node.js 18+** (for frontend)
- **npm or yarn** (package manager)
- **Poppler** (for PDF processing)
  - Windows: [Download here](https://github.com/oschwalde/poppler-windows/releases)
  - macOS: `brew install poppler`
  - Linux: `apt-get install poppler-utils`

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
# Navigate to the project directory
cd bridge-financial-spreading

# Create and configure .env file
cp env.example .env
# Edit .env and add your API keys:
# - OPENAI_API_KEY
# - LANGSMITH_API_KEY (optional but recommended)
```

### 2. Install Backend Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install backend-specific dependencies
pip install -r backend/requirements.txt
```

### 3. Install Frontend Dependencies

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Return to root
cd ..
```

### 4. Start the Application

You need to run both the backend and frontend servers.

#### Option A: Using Two Terminals

**Terminal 1 - Backend:**
```bash
python backend/main.py
```
The backend will start on `http://localhost:8000`

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
The frontend will start on `http://localhost:5173`

#### Option B: Using Scripts (Recommended)

Create a startup script for convenience:

**For Windows (`start.bat`):**
```batch
@echo off
start cmd /k "python backend/main.py"
timeout /t 2
start cmd /k "cd frontend && npm run dev"
```

**For macOS/Linux (`start.sh`):**
```bash
#!/bin/bash
# Start backend
python backend/main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
cd frontend
npm run dev &
FRONTEND_PID=$!

# Wait for user to stop
echo "Press Ctrl+C to stop all servers"
wait
```

Make it executable:
```bash
chmod +x start.sh
./start.sh
```

### 5. Access the Application

Open your browser and navigate to:
```
http://localhost:5173
```

## 📖 User Guide

### Uploading a Financial Statement

1. **Select a PDF**: Drag and drop a PDF or click to browse
2. **Choose Document Type**: Select "Income Statement" or "Balance Sheet"
3. **Fiscal Period (Auto)**: the app will automatically detect the most recent period from the statement headers using an AI vision pass. (Optional override is supported via the API by setting `period`.)
4. **Click "Process Statement"**: The AI will extract the data

### Viewing Results

After processing, you'll see:

- **Left Panel**: Original PDF with zoom and navigation controls
- **Right Panel**: Extracted financial data in structured tables
- **Confidence Indicators**:
  - 🟢 Green dot = High confidence (≥80%)
  - 🟡 Yellow dot = Medium confidence (50-80%)
  - 🔴 Red dot = Low confidence (<50%)

### Exploring Extraction Details

Hover over the ℹ️ icon next to any field to see:
- Confidence percentage
- Source text from the PDF
- Section where the data was found

### Exporting Data

Click the "Export" button to download:
- **JSON**: Full structured data with metadata
- **CSV**: Spreadsheet-compatible format

## 🔧 Configuration

### Backend Configuration

Edit `.env` in the project root:

```env
# Required
OPENAI_API_KEY=sk-your-key-here
LANGSMITH_API_KEY=lsv2_pt_your-key-here

# Optional
LANGSMITH_PROJECT=financial-spreader-v1
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
```

### Frontend Configuration

Create `frontend/.env.local`:

```env
# API URL (defaults to /api which proxies to backend)
VITE_API_URL=/api
```

## 📁 Project Structure

```
bridge-financial-spreading/
├── backend/
│   ├── api.py              # FastAPI application
│   ├── main.py             # Server entry point
│   ├── requirements.txt    # Backend dependencies
│   └── uploads/            # Uploaded PDFs (created automatically)
│
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   │   ├── Header.tsx
│   │   │   ├── UploadPage.tsx
│   │   │   ├── PDFViewer.tsx
│   │   │   ├── FinancialTable.tsx
│   │   │   ├── SpreadingView.tsx
│   │   │   ├── ExportMenu.tsx
│   │   │   └── ConfidenceBadge.tsx
│   │   ├── api.ts          # API client
│   │   ├── types.ts        # TypeScript types
│   │   ├── utils.ts        # Utility functions
│   │   ├── App.tsx         # Main app component
│   │   └── main.tsx        # React entry point
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── spreader.py             # Core spreading engine
├── models.py               # Pydantic schemas
├── utils.py                # PDF processing utilities
└── main.py                 # CLI entry point
```

## 🔌 API Reference

### POST `/api/spread`

Upload and process a financial statement PDF.

**Request:**
- `file` (File): PDF file
- `doc_type` (string): "income" or "balance"
- `period` (string, optional): Fiscal period. If omitted or set to `"Latest"`/`"Auto"`, the backend will auto-detect the most recent period from the statement headers.
- `max_pages` (integer, optional): Max pages to process
- `dpi` (integer, optional): PDF resolution (default: 200)

> **Note:** Prompts are loaded from LangSmith Hub. If Hub is unavailable, the request will fail with a clear error.

**Response:**
```json
{
  "success": true,
  "job_id": "uuid",
  "data": { /* IncomeStatement or BalanceSheet */ },
  "metadata": {
    "total_fields": 15,
    "high_confidence": 12,
    "medium_confidence": 2,
    "low_confidence": 1,
    "missing": 0,
    "extraction_rate": 1.0,
    "average_confidence": 0.89,
    "original_filename": "financials.pdf",
    "pdf_url": "/api/files/uuid_financials.pdf"
  }
}
```

### GET `/api/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### GET `/api/files/{filename}`

Retrieve uploaded PDF file.

## 🎨 Customization

### Changing Colors

Edit `frontend/tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: {
        // Your brand colors
      },
      confidence: {
        high: '#10b981',    // Green
        medium: '#f59e0b',  // Yellow
        low: '#ef4444',     // Red
      }
    }
  }
}
```

### Adding New Features

1. **Backend**: Add endpoints in `backend/api.py`
2. **Frontend**: Create components in `frontend/src/components/`
3. **API Integration**: Update `frontend/src/api.ts`

## 🐛 Troubleshooting

### Backend won't start

**Error**: `Module not found`
```bash
# Install all dependencies
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

**Error**: `OPENAI_API_KEY not set`
```bash
# Create .env file with your API key
cp env.example .env
# Edit .env and add your key
```

### Frontend won't start

**Error**: `Cannot find module`
```bash
cd frontend
npm install
```

**Error**: `Port 5173 already in use`
```bash
# Kill the process or change port in vite.config.ts
```

### PDF viewer not working

**Error**: `Failed to load PDF`
- Check that the backend is running
- Verify the PDF uploaded successfully
- Check browser console for CORS errors

### CORS errors

If you see CORS errors in the browser console:
1. Ensure backend is running on port 8000
2. Check that CORS middleware is enabled in `backend/api.py`
3. Verify frontend proxy configuration in `frontend/vite.config.ts`

## 🚀 Deployment

### Production Build

**Backend:**
```bash
# Use production WSGI server
pip install gunicorn
gunicorn backend.api:app -w 4 -k uvicorn.workers.UvicornWorker
```

**Frontend:**
```bash
cd frontend
npm run build
# Serve the dist/ folder with nginx or similar
```

### Environment Variables for Production

```env
# Backend
OPENAI_API_KEY=your-key
LANGSMITH_API_KEY=your-key
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=false

# Frontend (build time)
VITE_API_URL=https://your-api-domain.com/api
```

### Docker Deployment (Optional)

Create `Dockerfile` for containerized deployment:

```dockerfile
# Backend
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt backend/requirements.txt ./
RUN pip install -r requirements.txt -r backend/requirements.txt
COPY . .
CMD ["python", "backend/main.py"]
```

## 📊 Performance Tips

1. **DPI Settings**: Lower DPI (150) for faster processing, higher (300) for better accuracy
2. **Max Pages**: Limit pages for large documents to reduce processing time
3. **Caching**: Enable browser caching for faster repeated viewing
4. **Connection Pooling**: Use connection pooling for multiple requests

## 🔐 Security Considerations

- Never commit `.env` files with real API keys
- Use HTTPS in production
- Implement authentication for production deployments
- Set file upload size limits
- Validate all user inputs
- Configure proper CORS for production domains

## 📝 License

See the main project LICENSE file.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 💬 Support

For issues or questions:
- Check the troubleshooting section
- Review the main project README
- Check LangSmith traces for debugging

## 🙏 Acknowledgments

- Built with FastAPI, React, and TailwindCSS
- Powered by OpenAI Vision models
- Traced with LangSmith
