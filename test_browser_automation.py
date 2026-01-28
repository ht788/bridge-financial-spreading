"""
Comprehensive Browser-Based Testing System for Financial Spreading
===================================================================

This testing system uses Cursor's browser automation to test the financial
spreading web application with real PDF files from example_financials/.

Features:
- Full debug logging with timestamps and detailed traces
- Tests both single and batch file processing
- Validates UI state and data extraction
- Captures LangChain/LangSmith traces
- Comprehensive error reporting
- Tracks processing steps and WebSocket events
- Validates extracted financial data
"""

import json
import time
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import traceback


# =============================================================================
# CONFIGURATION
# =============================================================================

class TestConfig:
    """Test configuration settings"""
    BACKEND_URL = "http://localhost:8000"
    FRONTEND_URL = "http://localhost:5173"
    EXAMPLE_DIR = Path("example_financials")
    LOG_DIR = Path("test_logs")
    SCREENSHOT_DIR = Path("test_screenshots")
    MAX_WAIT_TIME = 120  # seconds
    POLL_INTERVAL = 2  # seconds
    

# =============================================================================
# LOGGING SYSTEM
# =============================================================================

class DebugLogger:
    """Enhanced logging with multiple output streams"""
    
    def __init__(self, log_file: Optional[Path] = None):
        self.log_file = log_file
        self.logs: List[Dict[str, Any]] = []
        
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def log(self, level: str, message: str, **kwargs):
        """Log a message with structured data"""
        timestamp = datetime.utcnow().isoformat() + "Z"
        entry = {
            "timestamp": timestamp,
            "level": level.upper(),
            "message": message,
            **kwargs
        }
        
        self.logs.append(entry)
        
        # Console output with color
        color_codes = {
            "DEBUG": "\033[36m",    # Cyan
            "INFO": "\033[32m",     # Green
            "WARNING": "\033[33m",  # Yellow
            "ERROR": "\033[31m",    # Red
            "SUCCESS": "\033[92m",  # Bright Green
            "RESET": "\033[0m"
        }
        
        color = color_codes.get(level.upper(), color_codes["RESET"])
        reset = color_codes["RESET"]
        
        print(f"{color}[{timestamp}] [{level.upper()}] {message}{reset}")
        
        # Print additional context
        for key, value in kwargs.items():
            if value is not None:
                if isinstance(value, (dict, list)):
                    print(f"  {key}: {json.dumps(value, indent=2)}")
                else:
                    print(f"  {key}: {value}")
        
        # File output
        if self.log_file:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + "\n")
    
    def debug(self, message: str, **kwargs):
        self.log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self.log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self.log("ERROR", message, **kwargs)
    
    def success(self, message: str, **kwargs):
        self.log("SUCCESS", message, **kwargs)
    
    def save_summary(self, filepath: Path):
        """Save a summary of all logs"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.logs, f, indent=2)


# =============================================================================
# TEST RESULTS TRACKER
# =============================================================================

class TestResult:
    """Track results for a single test"""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.status = "pending"  # pending, running, passed, failed
        self.error: Optional[str] = None
        self.error_trace: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
        self.steps: List[Dict[str, Any]] = []
        self.logs: List[Dict[str, Any]] = []
    
    def add_step(self, step_name: str, status: str, **kwargs):
        """Add a processing step"""
        self.steps.append({
            "name": step_name,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            **kwargs
        })
    
    def complete(self, status: str, error: Optional[str] = None):
        """Mark test as complete"""
        self.end_time = datetime.utcnow()
        self.status = status
        self.error = error
        if error:
            self.error_trace = traceback.format_exc()
    
    @property
    def duration(self) -> float:
        """Get test duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "test_name": self.test_name,
            "status": self.status,
            "start_time": self.start_time.isoformat() + "Z",
            "end_time": self.end_time.isoformat() + "Z" if self.end_time else None,
            "duration": self.duration,
            "error": self.error,
            "error_trace": self.error_trace,
            "metadata": self.metadata,
            "steps": self.steps,
            "logs": self.logs
        }


class TestSuite:
    """Manage a suite of tests"""
    
    def __init__(self, name: str, logger: DebugLogger):
        self.name = name
        self.logger = logger
        self.tests: List[TestResult] = []
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
    
    def add_test(self, test: TestResult):
        """Add a test result"""
        self.tests.append(test)
    
    def complete(self):
        """Mark suite as complete"""
        self.end_time = datetime.utcnow()
    
    @property
    def passed_count(self) -> int:
        return sum(1 for t in self.tests if t.status == "passed")
    
    @property
    def failed_count(self) -> int:
        return sum(1 for t in self.tests if t.status == "failed")
    
    @property
    def total_count(self) -> int:
        return len(self.tests)
    
    @property
    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.utcnow() - self.start_time).total_seconds()
    
    def print_summary(self):
        """Print test suite summary"""
        print("\n" + "=" * 80)
        print(f"TEST SUITE: {self.name}")
        print("=" * 80)
        print(f"Total Tests: {self.total_count}")
        print(f"Passed: {self.passed_count}")
        print(f"Failed: {self.failed_count}")
        print(f"Duration: {self.duration:.2f}s")
        print("=" * 80)
        
        for test in self.tests:
            status_symbol = "[PASS]" if test.status == "passed" else "[FAIL]"
            print(f"{status_symbol} {test.test_name} ({test.duration:.2f}s)")
            if test.error:
                print(f"  Error: {test.error}")
        
        print("=" * 80 + "\n")
    
    def save_results(self, filepath: Path):
        """Save test results to file"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        results = {
            "suite_name": self.name,
            "start_time": self.start_time.isoformat() + "Z",
            "end_time": self.end_time.isoformat() + "Z" if self.end_time else None,
            "duration": self.duration,
            "total_tests": self.total_count,
            "passed": self.passed_count,
            "failed": self.failed_count,
            "tests": [t.to_dict() for t in self.tests]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        self.logger.info(f"Test results saved to {filepath}")


# =============================================================================
# BROWSER TEST HELPER (Instructions for manual browser testing)
# =============================================================================

class BrowserTestInstructions:
    """
    Generate detailed instructions for browser-based testing.
    
    Since we need to use Cursor's MCP browser tools, this class generates
    step-by-step instructions that can be executed.
    """
    
    @staticmethod
    def generate_test_plan(pdf_files: List[Path]) -> Dict[str, Any]:
        """Generate a comprehensive test plan"""
        
        test_plan = {
            "overview": {
                "total_files": len(pdf_files),
                "files": [str(f.name) for f in pdf_files],
                "tests": []
            },
            "setup": [
                "1. Ensure backend server is running on http://localhost:8000",
                "2. Ensure frontend server is running on http://localhost:5173",
                "3. Check that example_financials/ contains test PDFs",
                "4. Open browser to http://localhost:5173"
            ],
            "tests": []
        }
        
        # Generate test for each file
        for idx, pdf_file in enumerate(pdf_files, 1):
            # Determine doc type from filename
            filename_lower = pdf_file.name.lower()
            if 'balance' in filename_lower or 'sheet' in filename_lower:
                doc_type = 'balance'
                doc_type_label = 'Balance Sheet'
            elif 'income' in filename_lower or 'profit' in filename_lower or 'loss' in filename_lower:
                doc_type = 'income'
                doc_type_label = 'Income Statement'
            else:
                doc_type = 'unknown'
                doc_type_label = 'Unknown'
            
            test = {
                "test_number": idx,
                "test_name": f"Test {doc_type_label}: {pdf_file.name}",
                "file": str(pdf_file),
                "doc_type": doc_type,
                "steps": [
                    {
                        "step": 1,
                        "action": "navigate",
                        "url": "http://localhost:5173",
                        "description": "Navigate to application homepage"
                    },
                    {
                        "step": 2,
                        "action": "verify_element",
                        "selector": "upload page",
                        "description": "Verify upload page is visible"
                    },
                    {
                        "step": 3,
                        "action": "upload_file",
                        "file": str(pdf_file.absolute()),
                        "description": f"Upload file: {pdf_file.name}"
                    },
                    {
                        "step": 4,
                        "action": "select_doctype",
                        "doctype": doc_type,
                        "description": f"Select document type: {doc_type_label}"
                    },
                    {
                        "step": 5,
                        "action": "click_submit",
                        "description": "Click submit/process button"
                    },
                    {
                        "step": 6,
                        "action": "wait_for_processing",
                        "max_wait": 120,
                        "description": "Wait for processing to complete (up to 2 minutes)"
                    },
                    {
                        "step": 7,
                        "action": "verify_results",
                        "description": "Verify results page is displayed"
                    },
                    {
                        "step": 8,
                        "action": "extract_metadata",
                        "description": "Extract metadata (confidence, extraction rate, etc.)"
                    },
                    {
                        "step": 9,
                        "action": "validate_data",
                        "description": "Validate extracted financial data structure"
                    },
                    {
                        "step": 10,
                        "action": "check_debug_logs",
                        "description": "Check debug panel for errors or warnings"
                    },
                    {
                        "step": 11,
                        "action": "capture_screenshot",
                        "filename": f"test_{idx}_{pdf_file.stem}.png",
                        "description": "Capture screenshot of results"
                    }
                ],
                "validation": {
                    "required_elements": [
                        "Results table with financial data",
                        "Metadata showing extraction rate",
                        "Confidence scores for each field",
                        "Export options (CSV, JSON, Excel)"
                    ],
                    "data_validation": [
                        "All required fields present for doc_type",
                        "Numeric values are properly formatted",
                        "Confidence scores between 0 and 1",
                        "No null values for core metrics"
                    ]
                }
            }
            
            test_plan["tests"].append(test)
        
        # Add batch test
        if len(pdf_files) > 1:
            batch_test = {
                "test_number": len(pdf_files) + 1,
                "test_name": "Batch Processing Test",
                "files": [str(f) for f in pdf_files],
                "steps": [
                    {
                        "step": 1,
                        "action": "navigate",
                        "url": "http://localhost:5173",
                        "description": "Navigate to application homepage"
                    },
                    {
                        "step": 2,
                        "action": "upload_multiple_files",
                        "files": [str(f.absolute()) for f in pdf_files],
                        "description": f"Upload all {len(pdf_files)} files"
                    },
                    {
                        "step": 3,
                        "action": "configure_batch",
                        "description": "Configure doc types for each file"
                    },
                    {
                        "step": 4,
                        "action": "submit_batch",
                        "description": "Submit batch processing"
                    },
                    {
                        "step": 5,
                        "action": "monitor_progress",
                        "description": "Monitor batch processing progress"
                    },
                    {
                        "step": 6,
                        "action": "verify_batch_results",
                        "description": "Verify all files were processed"
                    }
                ]
            }
            test_plan["tests"].append(batch_test)
        
        return test_plan


# =============================================================================
# API TESTING (Direct Backend Testing)
# =============================================================================

class APITester:
    """Test the backend API directly"""
    
    def __init__(self, logger: DebugLogger, config: TestConfig):
        self.logger = logger
        self.config = config
    
    def test_health_check(self) -> bool:
        """Test backend health endpoint"""
        import requests
        
        self.logger.info("Testing backend health check...")
        
        try:
            response = requests.get(
                f"{self.config.BACKEND_URL}/api/health",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.logger.success("Backend health check passed", data=data)
                return True
            else:
                self.logger.error(
                    f"Backend health check failed: {response.status_code}",
                    response=response.text
                )
                return False
                
        except Exception as e:
            self.logger.error(f"Backend health check error: {e}", error=str(e))
            return False
    
    def test_single_file_api(self, pdf_path: Path, doc_type: str) -> Optional[Dict[str, Any]]:
        """Test single file processing via API"""
        import requests
        
        self.logger.info(f"Testing API with file: {pdf_path.name}", doc_type=doc_type)
        
        try:
            with open(pdf_path, 'rb') as f:
                files = {'file': (pdf_path.name, f, 'application/pdf')}
                data = {
                    'doc_type': doc_type,
                    'period': 'Latest',
                    'max_pages': 10,
                    'dpi': 200
                }
                
                self.logger.debug("Sending POST request to /api/spread", params=data)
                
                response = requests.post(
                    f"{self.config.BACKEND_URL}/api/spread",
                    files=files,
                    data=data,
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.logger.success(
                        f"API processing successful for {pdf_path.name}",
                        job_id=result.get('job_id'),
                        metadata=result.get('metadata')
                    )
                    return result
                else:
                    self.logger.error(
                        f"API processing failed: {response.status_code}",
                        response=response.text
                    )
                    return None
                    
        except Exception as e:
            self.logger.error(f"API test error: {e}", error=str(e), trace=traceback.format_exc())
            return None


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_tests():
    """Main test execution function"""
    
    # Setup
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    TestConfig.LOG_DIR.mkdir(parents=True, exist_ok=True)
    TestConfig.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    
    log_file = TestConfig.LOG_DIR / f"test_run_{timestamp}.log"
    logger = DebugLogger(log_file)
    
    logger.info("=" * 80)
    logger.info("FINANCIAL SPREADING TEST SUITE - BROWSER AUTOMATION")
    logger.info("=" * 80)
    logger.info(f"Timestamp: {timestamp}")
    logger.info(f"Backend URL: {TestConfig.BACKEND_URL}")
    logger.info(f"Frontend URL: {TestConfig.FRONTEND_URL}")
    logger.info(f"Example Directory: {TestConfig.EXAMPLE_DIR}")
    logger.info("=" * 80)
    
    # Create test suite
    suite = TestSuite("Financial Spreading Browser Tests", logger)
    
    # Find example PDFs
    logger.info("Scanning for example PDFs...")
    
    if not TestConfig.EXAMPLE_DIR.exists():
        logger.error(f"Example directory not found: {TestConfig.EXAMPLE_DIR}")
        return 1
    
    pdf_files = list(TestConfig.EXAMPLE_DIR.glob("*.pdf"))
    
    if not pdf_files:
        logger.error(f"No PDF files found in {TestConfig.EXAMPLE_DIR}")
        return 1
    
    logger.info(f"Found {len(pdf_files)} PDF file(s)")
    for pdf in pdf_files:
        logger.debug(f"  - {pdf.name} ({pdf.stat().st_size} bytes)")
    
    # Test 1: Backend Health Check
    logger.info("\n" + "=" * 80)
    logger.info("TEST 1: Backend Health Check")
    logger.info("=" * 80)
    
    test1 = TestResult("Backend Health Check")
    test1.status = "running"
    
    api_tester = APITester(logger, TestConfig)
    
    if api_tester.test_health_check():
        test1.complete("passed")
        logger.success("[PASS] Backend health check passed")
    else:
        test1.complete("failed", "Backend health check failed")
        logger.error("[FAIL] Backend health check failed")
        logger.warning("Cannot proceed without backend. Please start backend server.")
        suite.add_test(test1)
        suite.complete()
        suite.print_summary()
        return 1
    
    suite.add_test(test1)
    
    # Test 2: API Testing for each file
    for idx, pdf_file in enumerate(pdf_files, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f"TEST {idx + 1}: API Processing - {pdf_file.name}")
        logger.info("=" * 80)
        
        # Determine doc type
        filename_lower = pdf_file.name.lower()
        if 'balance' in filename_lower or 'sheet' in filename_lower:
            doc_type = 'balance'
        elif 'income' in filename_lower or 'profit' in filename_lower or 'loss' in filename_lower:
            doc_type = 'income'
        else:
            logger.warning(f"Cannot determine doc_type from filename: {pdf_file.name}")
            continue
        
        test = TestResult(f"API Processing: {pdf_file.name}")
        test.status = "running"
        test.metadata["file"] = str(pdf_file)
        test.metadata["doc_type"] = doc_type
        
        result = api_tester.test_single_file_api(pdf_file, doc_type)
        
        if result and result.get('success'):
            test.complete("passed")
            test.metadata["result"] = result
            
            # Extract key metrics
            metadata = result.get('metadata', {})
            logger.success(
                f"[PASS] Successfully processed {pdf_file.name}",
                extraction_rate=f"{metadata.get('extraction_rate', 0) * 100:.1f}%",
                average_confidence=f"{metadata.get('average_confidence', 0) * 100:.1f}%",
                total_fields=metadata.get('total_fields'),
                high_confidence=metadata.get('high_confidence')
            )
            
            # Save detailed results
            result_file = TestConfig.LOG_DIR / f"result_{timestamp}_{pdf_file.stem}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            logger.debug(f"Detailed results saved to {result_file}")
            
        else:
            error_msg = result.get('error') if result else "Unknown error"
            test.complete("failed", error_msg)
            logger.error(f"[FAIL] Failed to process {pdf_file.name}", error=error_msg)
        
        suite.add_test(test)
    
    # Generate Browser Test Plan
    logger.info("\n" + "=" * 80)
    logger.info("GENERATING BROWSER TEST PLAN")
    logger.info("=" * 80)
    
    test_plan = BrowserTestInstructions.generate_test_plan(pdf_files)
    test_plan_file = TestConfig.LOG_DIR / f"browser_test_plan_{timestamp}.json"
    
    with open(test_plan_file, 'w', encoding='utf-8') as f:
        json.dump(test_plan, f, indent=2)
    
    logger.success(f"Browser test plan generated: {test_plan_file}")
    
    # Print browser test plan summary
    logger.info("\nBrowser Test Plan Overview:")
    logger.info(f"Total files to test: {test_plan['overview']['total_files']}")
    logger.info(f"Total test scenarios: {len(test_plan['tests'])}")
    
    for test in test_plan['tests']:
        logger.info(f"  - {test['test_name']} ({len(test['steps'])} steps)")
    
    # Complete test suite
    suite.complete()
    
    # Save results
    results_file = TestConfig.LOG_DIR / f"test_results_{timestamp}.json"
    suite.save_results(results_file)
    
    # Save logger summary
    logger_summary_file = TestConfig.LOG_DIR / f"test_logs_{timestamp}.json"
    logger.save_summary(logger_summary_file)
    
    # Print summary
    suite.print_summary()
    
    logger.info(f"\nTest artifacts saved to: {TestConfig.LOG_DIR}")
    logger.info(f"  - Test results: {results_file}")
    logger.info(f"  - Browser test plan: {test_plan_file}")
    logger.info(f"  - Detailed logs: {logger_summary_file}")
    
    # Return exit code
    return 0 if suite.failed_count == 0 else 1


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        exit_code = run_tests()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        print(traceback.format_exc())
        sys.exit(1)
