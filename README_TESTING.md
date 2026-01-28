# Browser Testing System for Financial Spreading

This directory contains a comprehensive testing system designed to test the Financial Spreading application using **Cursor's built-in MCP browser tools**.

## Overview

The testing system provides:
- **Automated API testing** - Tests backend endpoints directly
- **Browser automation guide** - Step-by-step instructions for browser testing
- **Comprehensive logging** - Debug logs, screenshots, and trace analysis
- **LangChain debugging** - Specific checks for LangChain/LangSmith issues

## Files

### 1. `test_browser_automation.py`
Main test automation script that includes:
- API health checks
- Single file processing tests
- Debug logging with structured output
- Test result tracking and reporting
- Browser test plan generation

### 2. `test_browser_executor.py`
Generates Cursor-specific browser commands in JSON format for execution.

### 3. `test_browser_live.py`
Generates interactive test guide and report templates for manual/assisted testing.

## Quick Start

### Prerequisites

1. **Start the servers:**
   ```bash
   # Terminal 1: Backend
   python backend/main.py
   
   # Terminal 2: Frontend
   cd frontend
   npm run dev
   ```

2. **Verify configuration:**
   - Backend on: `http://localhost:8000`
   - Frontend on: `http://localhost:5173`
   - `.env` file with API keys configured

3. **Verify example files exist:**
   ```
   example_financials/
     - FOMIN+LLC_Balance+Sheet--.pdf
     - FOMIN+LLC_Profit+and+Loss--.pdf
   ```

### Running API Tests

```bash
python test_browser_automation.py
```

This will:
- ✓ Test backend health endpoint
- ✓ Process each PDF via API
- ✓ Generate detailed logs and results
- ✓ Save results to `test_logs/`
- ✓ Create browser test plan

### Running Browser Tests with Cursor

**Use the Cursor AI assistant to execute browser tests:**

1. **Ask Cursor to start the test:**
   ```
   "I need to test the financial spreading application using browser automation.
   Navigate to http://localhost:5173"
   ```

2. **Follow the test sequence for each file:**

#### Test Sequence for Each PDF

**File 1: Balance Sheet**
```
Step 1: Navigate to http://localhost:5173
Step 2: Take a snapshot to see the page elements
Step 3: Upload file: example_financials/FOMIN+LLC_Balance+Sheet--.pdf
Step 4: Select document type: balance
Step 5: Click submit/process button
Step 6: Wait and monitor processing (take snapshots every 5 seconds)
Step 7: Take full page screenshot when complete
Step 8: Open debug panel
Step 9: Take screenshot of debug logs
Step 10: Analyze logs for errors or warnings
```

**File 2: Income Statement**
```
Step 1: Click back button to return to upload page
Step 2: Upload file: example_financials/FOMIN+LLC_Profit+and+Loss--.pdf
Step 3: Select document type: income
Step 4: Click submit/process button
Step 5: Wait and monitor processing
Step 6: Capture results and debug logs
```

### Example Cursor Commands

Here are specific commands to use with Cursor AI:

```
"Navigate to http://localhost:5173"

"Take a snapshot of the current page"

"Click the file upload button"

"Help me upload the file from example_financials/FOMIN+LLC_Balance+Sheet--.pdf"

"Select 'balance' from the document type dropdown"

"Click the submit button"

"Take a snapshot every 5 seconds to monitor progress"

"Take a full page screenshot named 'test_balance_sheet_results.png'"

"Click the debug panel button"

"Take a screenshot of the debug panel"
```

## Test Results

### Output Directories

- `test_logs/` - JSON logs and test results
- `test_screenshots/` - Browser screenshots
- `langsmith_traces/` - LangSmith trace exports (if configured)

### Generated Files

After running tests, you'll have:
- `test_logs/test_run_YYYYMMDD_HHMMSS.log` - Main test log
- `test_logs/test_results_YYYYMMDD_HHMMSS.json` - Test results summary
- `test_logs/browser_test_plan_YYYYMMDD_HHMMSS.json` - Detailed browser test plan
- `test_logs/result_YYYYMMDD_HHMMSS_*.json` - Individual file results
- `test_logs/test_report_YYYYMMDD_HHMMSS.md` - Markdown report template

## What to Look For

### Success Indicators
- ✓ File uploads successfully
- ✓ Processing completes within 2 minutes
- ✓ Results table shows extracted data
- ✓ Metadata shows extraction rate > 70%
- ✓ Average confidence > 0.7
- ✓ No ERROR level logs
- ✓ Export functionality works

### Common Issues

#### LangChain/LangSmith Issues
- **"Hub prompt not found"** - Prompts not in LangSmith Hub (will use fallback)
- **"API key not configured"** - Missing OpenAI or LangSmith key
- **"Rate limit exceeded"** - Too many API calls, wait and retry
- **"Validation error"** - Pydantic schema mismatch, check models
- **"Token limit exceeded"** - PDF too large or complex

#### Application Issues
- **File upload fails** - Check file size, format, browser compatibility
- **Timeout** - Large PDFs or slow API response
- **WebSocket disconnects** - Network issues, check connection
- **Empty results** - Extraction failed, check debug logs

### Debug Log Analysis

When reviewing debug logs, pay attention to:

1. **Log Levels:**
   - ERROR - Critical failures
   - WARNING - Potential issues
   - INFO - Normal operations
   - DEBUG - Detailed traces

2. **Key Events:**
   - File upload and save
   - PDF to image conversion
   - LangChain model invocation
   - Structured output validation
   - Result extraction

3. **LangSmith Traces:**
   - Trace ID for each operation
   - Model used (gpt-5.2, gpt-4o, etc.)
   - Token counts
   - Response times
   - Any retries or errors

4. **Performance Metrics:**
   - Processing time per file
   - API response times
   - Token usage
   - Success/failure rate

## Advanced Testing

### Batch Processing Test

Upload multiple files at once:
```
"Upload both PDF files from example_financials/"
"Configure doc types: balance for first, income for second"
"Click submit to process batch"
"Monitor batch progress"
"Take screenshot of batch results"
```

### Error Handling Tests

Test error scenarios:
- Upload non-PDF file
- Upload corrupted PDF
- Stop backend during processing
- Test with missing API keys
- Test large multi-page PDFs

### Performance Testing

Monitor for:
- Processing time < 60 seconds per page
- Memory usage stable
- No memory leaks
- Proper cleanup after processing

## Troubleshooting

### Backend Not Running
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Start backend
python backend/main.py
```

### Frontend Not Running
```bash
# Check if port 5173 is in use
netstat -ano | findstr :5173

# Start frontend
cd frontend
npm run dev
```

### Missing Dependencies
```bash
# Backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### API Key Issues
Check `.env` file:
```bash
OPENAI_API_KEY=sk-...
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=financial-spreader-v1
```

## Next Steps

After testing:
1. Review all test results in `test_logs/`
2. Check screenshots in `test_screenshots/`
3. Visit LangSmith dashboard for traces
4. Document any issues found
5. Create GitHub issues for bugs
6. Iterate on fixes and re-test

## Support

For issues or questions:
1. Check debug logs in `test_logs/`
2. Review LangSmith traces
3. Check backend console output
4. Check frontend console (F12 in browser)
5. Review this testing guide

---

**Happy Testing! 🚀**
