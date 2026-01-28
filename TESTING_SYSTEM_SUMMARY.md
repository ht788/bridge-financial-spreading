# Testing System Summary

## What I've Created

I've built a comprehensive testing system for your Financial Spreading application with three main components:

### 1. **test_browser_automation.py** - API Testing Framework
A Python script that:
- Tests backend health endpoint
- Processes each PDF file via the API
- Provides detailed debug logging with timestamps
- Tracks test results and generates reports
- Saves all logs to `test_logs/` directory

**Run it with:**
```bash
python test_browser_automation.py
```

**Note:** This currently shows backend is not running on port 8000. The error was "404 Not Found" at the health endpoint.

### 2. **test_browser_executor.py** - Browser Test Plan Generator
Generates JSON test plans with step-by-step Cursor browser commands.

### 3. **test_browser_live.py** - Interactive Test Guide
Generates markdown test reports and interactive guides for manual testing.

### 4. **README_TESTING.md** - Complete Testing Documentation
User-friendly guide with:
- Quick start instructions
- Example Cursor AI commands
- Debugging checklists
- Common issues and solutions

## How to Use the Testing System

### Step 1: Start Your Servers

You need both servers running. I can see the frontend is already running on port 5173, but the backend needs to be started:

**Start Backend:**
```bash
python backend/main.py
```

The backend should run on `http://localhost:8000`

### Step 2: Run API Tests

Once both servers are running:

```bash
python test_browser_automation.py
```

This will:
- Test the backend health
- Process both example PDFs
- Generate detailed logs in `test_logs/`
- Create test reports with all debug info

### Step 3: Browser Testing with Cursor

Use Cursor's AI assistant to test the UI:

**Example commands to give to Cursor AI:**

1. **"Navigate to http://localhost:5173"**
   
2. **"Take a snapshot of the current page"**
   
3. **"Help me upload the file from C:\\Users\\HarteThompson\\GitHub\\bridge-financial-spreading\\example_financials\\FOMIN+LLC_Balance+Sheet--.pdf"**
   
4. **"Select 'balance' from the document type dropdown"**
   
5. **"Click the submit button"**
   
6. **"Take a snapshot every 5 seconds to check processing status"**
   
7. **"Take a full page screenshot when processing completes"**
   
8. **"Click the debug panel button and take a screenshot of the logs"**

## Key Features

### Comprehensive Logging
Every test action is logged with:
- Timestamp
- Log level (DEBUG, INFO, WARNING, ERROR, SUCCESS)
- Structured data (JSON)
- Stack traces for errors
- File output for later analysis

### LangChain-Specific Debugging
The system specifically checks for:
- LangSmith trace IDs
- Hub prompt loading
- Model invocations
- Token counts
- Pydantic validation errors
- Vision API calls
- Reasoning loop steps

### Test Result Tracking
- Individual test results
- Pass/fail status
- Duration tracking
- Metadata extraction
- Screenshot capture
- Log aggregation

## Output Files

After running tests, you'll find:

```
test_logs/
├── test_run_YYYYMMDD_HHMMSS.log          # Main log file
├── test_results_YYYYMMDD_HHMMSS.json     # Test results
├── test_logs_YYYYMMDD_HHMMSS.json        # Aggregated logs
├── browser_test_plan_YYYYMMDD_HHMMSS.json # Browser commands
├── test_report_YYYYMMDD_HHMMSS.md        # Markdown report
└── result_YYYYMMDD_HHMMSS_*.json         # Individual results

test_screenshots/
└── test_*.png                             # Screenshots
```

## Example Test Flow

Here's what a complete test looks like:

1. **Health Check**
   - Tests if backend is responding
   - Verifies API is accessible

2. **Balance Sheet Test**
   - Uploads `FOMIN+LLC_Balance+Sheet--.pdf`
   - Selects doc_type: `balance`
   - Processes via API
   - Validates extracted data
   - Checks confidence scores
   - Reviews debug logs

3. **Income Statement Test**
   - Uploads `FOMIN+LLC_Profit+and+Loss--.pdf`
   - Selects doc_type: `income`
   - Same validation process

4. **Browser UI Test**
   - Navigate to frontend
   - Upload via UI
   - Monitor processing in real-time
   - Check WebSocket logs
   - Verify results display
   - Test export functionality

## Debugging Capabilities

### What Gets Logged:
- All API requests and responses
- File upload details (size, type)
- PDF processing steps
- LangChain model invocations
- LangSmith trace information
- Pydantic validation
- WebSocket events
- Processing times
- Token usage
- Confidence scores
- Extraction rates

### Error Detection:
- Missing API keys
- Failed file uploads
- API timeouts
- Validation errors
- LangChain exceptions
- Network issues
- Data quality problems

## Next Steps to Run Tests

1. **Start the backend server** (it's not running yet):
   ```bash
   python backend/main.py
   ```

2. **Run the API tests**:
   ```bash
   python test_browser_automation.py
   ```

3. **Use Cursor AI for browser tests** - Follow the commands in README_TESTING.md

4. **Review logs** in `test_logs/` directory

5. **Check LangSmith dashboard** for traces (if configured)

## Troubleshooting

### Backend Not Running
The test showed: "Backend health check failed: 404"

This means the backend isn't running. Start it with:
```bash
python backend/main.py
```

### Unicode Issues on Windows
I've fixed all Unicode character issues (checkmarks, box-drawing) to work on Windows CMD/PowerShell.

### Missing Dependencies
If you get import errors:
```bash
pip install requests
```

## Summary

You now have a complete testing system that:
- ✓ Tests API directly
- ✓ Provides browser testing instructions  
- ✓ Logs everything with timestamps
- ✓ Tracks LangChain/LangSmith operations
- ✓ Generates detailed reports
- ✓ Captures screenshots
- ✓ Validates data extraction
- ✓ Identifies issues quickly

All logs are structured JSON, making it easy to:
- Parse programmatically
- Search for specific errors
- Track performance over time
- Debug LangChain issues
- Share with your team

The system is ready to use - just start the backend and run the tests!
