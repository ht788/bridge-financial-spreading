# Quick Start Guide - Testing the Application

## ✅ Step 1: Dependencies Installed
All Python packages are installed! ✓

## ⚙️ Step 2: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Copy the example
cp env.example .env
```

Then edit `.env` and add your API keys:

```env
# REQUIRED: OpenAI API Key
OPENAI_API_KEY=sk-your-actual-key-here

# Optional: LangSmith (needed for Hub prompts, but you can use --fallback-prompt for testing)
# LANGCHAIN_API_KEY=lsv2_your-key-here
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_PROJECT=financial-spreader-v1
```

**Minimum required**: Just `OPENAI_API_KEY` for testing with `--fallback-prompt`

## 📄 Step 3: Install Poppler (Required for PDF Processing)

**Windows:**
1. Download Poppler from: https://github.com/osmar81.de/poppler-windows/releases
2. Extract to a folder (e.g., `C:\poppler`)
3. Add `C:\poppler\Library\bin` to your Windows PATH environment variable
4. Restart your terminal

**macOS:**
```bash
brew install poppler
```

**Linux:**
```bash
sudo apt-get install poppler-utils
```

## 🧪 Step 4: Test the Application

### Option A: Test with Fallback Prompt (No LangSmith Hub needed)

```bash
# Basic test (you'll need a PDF file)
python main.py your_financial_statement.pdf income --fallback-prompt --verbose --pretty

# Test with balance sheet
python main.py your_balance_sheet.pdf balance --fallback-prompt --verbose --pretty

# Save output to file
python main.py document.pdf income --fallback-prompt --output result.json --pretty
```

### Option B: Test with LangSmith Hub (Requires Hub prompts set up)

```bash
# First, create prompts in LangSmith Hub:
# - financial-spreader/income-statement
# - financial-spreader/balance-sheet

# Then run without --fallback-prompt
python main.py document.pdf income --verbose --pretty
```

## 📋 Example Commands

```bash
# Test with verbose logging
python main.py sample.pdf income --fallback-prompt --verbose

# Test with specific period
python main.py financials.pdf income --period "FY2024" --fallback-prompt --pretty

# Test balance sheet
python main.py balance.pdf balance --fallback-prompt --output balance_output.json

# Limit to first 2 pages (for faster testing)
python main.py large_document.pdf income --max-pages 2 --fallback-prompt --verbose
```

## 🔍 Troubleshooting

### Error: "pdf2image" or "Poppler" not found
- **Solution**: Install Poppler (see Step 3 above)
- **Windows**: Make sure Poppler bin directory is in PATH

### Error: "OPENAI_API_KEY not set"
- **Solution**: Create `.env` file with your OpenAI API key

### Error: "Failed to pull prompt from Hub"
- **Solution**: Use `--fallback-prompt` flag for testing without LangSmith Hub

### Error: "File not found"
- **Solution**: Use full path to PDF or ensure you're in the correct directory

## 🎯 What to Expect

When you run the application, you'll see:
1. Log messages showing PDF conversion progress
2. Token usage estimates
3. Extraction summary (high/low confidence counts)
4. JSON output with structured financial data

Example output structure:
```json
{
  "revenue": {
    "value": 1000000,
    "confidence": 0.95,
    "raw_fields_used": ["Total Revenue"],
    "source_section_hint": null
  },
  "cogs": { ... },
  ...
}
```

## 🚀 Next Steps

1. **Get a sample PDF**: Use any financial statement PDF to test
2. **Run with fallback**: `python main.py sample.pdf income --fallback-prompt --verbose`
3. **Review output**: Check the JSON structure and confidence scores
4. **Set up LangSmith Hub**: Create prompts for production use (see README.md)
