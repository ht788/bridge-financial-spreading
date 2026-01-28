"""
Live Browser Testing with Cursor MCP Tools
===========================================

This script actually executes browser tests using Cursor's MCP browser tools.
It provides comprehensive logging and debugging output to help identify
issues with LangChain and the application.

Run this with the Cursor AI assistant to execute live browser tests.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


# =============================================================================
# TEST CONFIGURATION
# =============================================================================

FRONTEND_URL = "http://localhost:5173"
BACKEND_URL = "http://localhost:8000"
EXAMPLE_DIR = Path("example_financials")
LOG_DIR = Path("test_logs")
SCREENSHOT_DIR = Path("test_screenshots")


# =============================================================================
# MANUAL EXECUTION GUIDE
# =============================================================================

def print_execution_guide():
    """
    Print a guide for manually executing browser tests with Cursor AI.
    """
    
    print("""
================================================================================
                   CURSOR BROWSER TESTING GUIDE                               
                   for Financial Spreading Application                         
================================================================================

This guide will help you execute comprehensive browser tests using Cursor's
built-in MCP browser tools. Follow each step carefully and record the results.

================================================================================
PREREQUISITES
================================================================================

[ ] Backend server running on http://localhost:8000
    Command: python backend/main.py

[ ] Frontend server running on http://localhost:5173
    Command: cd frontend && npm run dev

[ ] Example PDF files in example_financials/ directory

[ ] .env file configured with:
    - OPENAI_API_KEY
    - LANGSMITH_API_KEY
    - LANGSMITH_PROJECT

================================================================================
TEST SEQUENCE 1: SINGLE FILE UPLOAD TEST
================================================================================
""")
    
    # Find PDF files
    pdf_files = list(EXAMPLE_DIR.glob("*.pdf"))
    
    for idx, pdf_file in enumerate(pdf_files, 1):
        filename_lower = pdf_file.name.lower()
        if 'balance' in filename_lower or 'sheet' in filename_lower:
            doc_type = 'balance'
            doc_type_label = 'Balance Sheet'
        elif 'income' in filename_lower or 'profit' in filename_lower:
            doc_type = 'income'
            doc_type_label = 'Income Statement'
        else:
            continue
        
        print(f"""
TEST {idx}: {doc_type_label} - {pdf_file.name}
───────────────────────────────────────────────────────────────────────────────

Step 1: Navigate to Application
    Ask Cursor AI: "Navigate to {FRONTEND_URL}"
    Expected: Upload page loads successfully

Step 2: Take Initial Snapshot
    Ask Cursor AI: "Take a snapshot of the current page"
    Expected: See upload form with file input and doc type selector
    
Step 3: Analyze Page Elements
    Review the snapshot and identify:
    □ File upload input/button
    □ Document type selector/dropdown
    □ Submit/Process button
    □ Any visible errors or issues

Step 4: Upload File (Manual or Assisted)
    File Path: {pdf_file.absolute()}
    Ask Cursor AI: "Help me upload the file {pdf_file.absolute()}"
    Expected: File appears in upload queue
    
    IMPORTANT: Note any errors during upload!

Step 5: Select Document Type
    Ask Cursor AI: "Select '{doc_type}' from the document type selector"
    Expected: Document type is set to {doc_type_label}

Step 6: Submit for Processing
    Ask Cursor AI: "Click the submit/process button"
    Expected: Processing begins, loading indicator appears

Step 7: Monitor Processing
    Ask Cursor AI every 5 seconds: "Take a snapshot to check progress"
    Watch for:
    □ Processing steps appearing
    □ Progress indicators
    □ Any error messages
    □ WebSocket connection status
    
    Continue monitoring until processing completes (max 2 minutes)

Step 8: Capture Results
    When processing completes:
    Ask Cursor AI: "Take a full page screenshot named 'test_{idx}_{pdf_file.stem}_results.png'"
    
    Expected Results:
    □ Financial data displayed in table format
    □ Metadata showing extraction rate and confidence
    □ No error messages
    □ Export options visible

Step 9: Open Debug Panel
    Ask Cursor AI: "Click the debug panel button to open debug logs"
    Expected: Debug panel opens with logs

Step 10: Analyze Debug Logs
    Ask Cursor AI: "Take a snapshot of the debug panel"
    
    Review logs for:
    □ All log levels (DEBUG, INFO, WARNING, ERROR)
    □ LangChain/LangSmith trace information
    □ API request/response logs
    □ Processing step details
    □ Any validation errors
    □ Timing information
    
    CRITICAL: Copy any ERROR or WARNING messages!

Step 11: Check WebSocket Logs
    In the debug panel, look for:
    □ WebSocket connection status
    □ Real-time log streaming
    □ Processing step updates
    
Step 12: Validate Extracted Data
    Check the results table:
    □ All expected fields present for {doc_type_label}
    □ Numeric values properly formatted
    □ Confidence scores between 0.0 and 1.0
    □ Reasonable values (no obvious errors)

Step 13: Test Export Functionality
    Ask Cursor AI: "Click the export button and select JSON"
    Expected: JSON export downloads successfully
    
    Validate the exported JSON:
    □ Valid JSON structure
    □ All data fields present
    □ Proper formatting

Step 14: Go Back to Upload Page
    Ask Cursor AI: "Click the back button to return to upload page"
    Expected: Returns to clean upload page, ready for next test

───────────────────────────────────────────────────────────────────────────────
DEBUGGING CHECKLIST FOR TEST {idx}
───────────────────────────────────────────────────────────────────────────────

Record any issues found:

□ File upload issues?
  - Could not select file
  - File not recognized
  - Upload failed

□ Processing issues?
  - Timeout
  - API errors
  - LangChain errors
  - Validation errors

□ Display issues?
  - Results not showing
  - Formatting problems
  - Missing data

□ LangSmith/LangChain specific issues?
  - Trace not appearing
  - Hub prompt not loading
  - Model errors
  - Token limit errors
  - Rate limiting

□ WebSocket issues?
  - Connection failed
  - Logs not streaming
  - Connection dropping

□ Data quality issues?
  - Low confidence scores
  - Missing fields
  - Incorrect values
  - Math errors (e.g., totals don't add up)

───────────────────────────────────────────────────────────────────────────────
""")
    
    print("""
═══════════════════════════════════════════════════════════════════════════════
TEST SEQUENCE 2: BATCH UPLOAD TEST
═══════════════════════════════════════════════════════════════════════════════

This test uploads multiple files at once.

Step 1: Navigate to Application
    Ask Cursor AI: "Navigate to {FRONTEND_URL}"

Step 2: Upload Multiple Files
    Ask Cursor AI: "Help me upload these files:"
""")
    
    for pdf in pdf_files:
        print(f"    - {pdf.absolute()}")
    
    print("""
Step 3: Configure Each File
    For each file, set the appropriate document type
    
Step 4: Submit Batch
    Ask Cursor AI: "Click submit to process all files"
    
Step 5: Monitor Batch Progress
    Watch for:
    □ Progress indicator showing X/N files
    □ Individual file status updates
    □ Overall batch status
    
Step 6: Review Batch Results
    Ask Cursor AI: "Take a screenshot of batch results"
    
    Check:
    □ All files processed
    □ Success/failure count
    □ Ability to view individual results

Step 7: Check Debug Logs
    Review logs for:
    □ Batch processing flow
    □ Individual file traces
    □ Any batch-level errors

═══════════════════════════════════════════════════════════════════════════════
TEST SEQUENCE 3: ERROR HANDLING TEST
═══════════════════════════════════════════════════════════════════════════════

Step 1: Test Invalid File Type
    Try uploading a .txt or .docx file
    Expected: Should show error message, not crash

Step 2: Test Missing API Keys
    (Only if safe to test) Temporarily remove OPENAI_API_KEY
    Expected: Should show clear error message about missing key

Step 3: Test Network Interruption
    Stop backend server during processing
    Expected: Should show connection error, attempt reconnection

Step 4: Test Large File
    (If available) Try a multi-page PDF
    Expected: Should handle gracefully, possibly with progress updates

═══════════════════════════════════════════════════════════════════════════════
LANGCHAIN-SPECIFIC DEBUGGING
═══════════════════════════════════════════════════════════════════════════════

When reviewing debug logs, pay special attention to:

1. LangSmith Trace IDs
   - Each operation should have a unique trace ID
   - Traces should appear in LangSmith dashboard
   - Check: https://smith.langchain.com

2. Hub Prompt Loading
   - Look for "Loading prompt from Hub" messages
   - Check for fallback to local prompts
   - Verify correct prompt version

3. Model Invocation
   - Model name (gpt-5.2, gpt-4o, etc.)
   - Token counts (input/output)
   - Response times
   - Any rate limiting messages

4. Structured Output
   - Pydantic validation passes
   - All required fields present
   - Type validation successful

5. Vision Processing
   - PDF to image conversion
   - Image encoding
   - Vision API calls
   - Image size/quality

6. Reasoning Loop
   - Initial extraction attempt
   - Validation checks
   - Retry attempts (if validation fails)
   - Final result acceptance

7. Common LangChain Issues to Watch For:
   □ "Hub prompt not found" - prompts not in LangSmith Hub
   □ "API key not configured" - missing/invalid OpenAI key
   □ "Rate limit exceeded" - too many API calls
   □ "Token limit exceeded" - input too large
   □ "Validation error" - Pydantic schema mismatch
   □ "Vision API error" - image processing issues
   □ "Timeout" - API or processing timeout

═══════════════════════════════════════════════════════════════════════════════
RECORDING RESULTS
═══════════════════════════════════════════════════════════════════════════════

After completing all tests, compile a report with:

1. Test Summary
   - Total tests run
   - Passed / Failed
   - Duration

2. Screenshots
   - All result pages
   - Debug panel with logs
   - Any error states

3. Log Excerpts
   - All ERROR messages
   - All WARNING messages
   - Key INFO messages (start, complete, metrics)

4. LangSmith Links
   - Trace URLs for each test
   - Project dashboard link

5. Issues Found
   - Description
   - Steps to reproduce
   - Expected vs actual behavior
   - Proposed fixes

6. Performance Metrics
   - Processing time per file
   - API response times
   - Token usage
   - Success rate

═══════════════════════════════════════════════════════════════════════════════
NEXT STEPS
═══════════════════════════════════════════════════════════════════════════════

After testing:
1. Save all screenshots to test_screenshots/
2. Save debug logs to test_logs/
3. Document issues in GitHub issues or a markdown file
4. Share LangSmith trace links with team
5. Iterate on fixes and re-test

═══════════════════════════════════════════════════════════════════════════════
""")


# =============================================================================
# AUTOMATED TEST HELPER
# =============================================================================

def generate_test_report_template():
    """Generate a markdown template for recording test results"""
    
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_file = LOG_DIR / f"test_report_{timestamp}.md"
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    pdf_files = list(EXAMPLE_DIR.glob("*.pdf"))
    
    template = f"""# Browser Test Report
**Generated:** {datetime.utcnow().isoformat()}Z
**Tester:** [Your Name]
**Environment:** Development

## Test Configuration
- Backend URL: {BACKEND_URL}
- Frontend URL: {FRONTEND_URL}
- Example Files: {len(pdf_files)}

## Test Files
"""
    
    for idx, pdf in enumerate(pdf_files, 1):
        template += f"{idx}. `{pdf.name}` ({pdf.stat().st_size} bytes)\n"
    
    template += """
## Test Results Summary

| Test | Status | Duration | Notes |
|------|--------|----------|-------|
"""
    
    for idx, pdf in enumerate(pdf_files, 1):
        template += f"| Test {idx}: {pdf.stem} | ⏳ PENDING | - | |\n"
    
    template += """
## Detailed Test Results

"""
    
    for idx, pdf in enumerate(pdf_files, 1):
        template += f"""
### Test {idx}: {pdf.name}

**Status:** ⏳ PENDING

**Screenshot:** `test_{idx}_{pdf.stem}_results.png`

**Processing Time:** -

**Extraction Metrics:**
- Extraction Rate: -
- Average Confidence: -
- Total Fields: -
- High Confidence Fields: -

**Issues Found:**
- [ ] None

**Debug Logs:**
```
[Paste relevant debug logs here]
```

**LangSmith Trace:** [Link to trace]

**Notes:**

---

"""
    
    template += """
## Batch Test Results

**Status:** ⏳ PENDING

**Files Processed:** 0 / 0

**Success Rate:** -

**Issues Found:**
- [ ] None

---

## Error Analysis

### Errors Found
[List all errors with details]

### Warnings Found
[List all warnings with details]

### LangChain-Specific Issues
[Any issues related to LangChain, LangSmith, prompts, models, etc.]

---

## Performance Analysis

### Response Times
- Average processing time per file: -
- Fastest: -
- Slowest: -

### Token Usage
[If available from LangSmith]
- Total tokens: -
- Average per file: -

### API Calls
- Total API calls: -
- Failed calls: -

---

## Recommendations

1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]

---

## Appendix

### Screenshots
[List all screenshots with descriptions]

### Log Files
[List all log files generated]

### LangSmith Traces
[List all trace URLs]
"""
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(template)
    
    print(f"\n[OK] Test report template created: {report_file}")
    print(f"  Fill in this template as you complete each test.\n")
    
    return report_file


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main function"""
    print("\n" + "="*80)
    print("CURSOR BROWSER TESTING SYSTEM")
    print("Financial Spreading Application")
    print("="*80 + "\n")
    
    # Check for example files
    if not EXAMPLE_DIR.exists():
        print(f"❌ ERROR: Example directory not found: {EXAMPLE_DIR}")
        return 1
    
    pdf_files = list(EXAMPLE_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ ERROR: No PDF files found in {EXAMPLE_DIR}")
        return 1
    
    print(f"[OK] Found {len(pdf_files)} PDF file(s) for testing\n")
    
    # Generate test report template
    report_file = generate_test_report_template()
    
    # Print execution guide
    print("\nPrinting execution guide...\n")
    print_execution_guide()
    
    print("\n" + "="*80)
    print("TEST SETUP COMPLETE")
    print("="*80)
    print(f"\nTest report template: {report_file}")
    print(f"Screenshots will be saved to: {SCREENSHOT_DIR}/")
    print(f"Logs will be saved to: {LOG_DIR}/")
    print("\nFollow the guide above to execute tests using Cursor's AI assistant.")
    print("Record your findings in the test report template.")
    print("="*80 + "\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
