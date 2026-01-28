"""
Browser Test Executor using Cursor MCP Browser Tools
=====================================================

This script provides step-by-step instructions for executing browser tests
using Cursor's MCP browser automation tools.

Usage:
    1. Run this script to generate test instructions
    2. Follow the instructions to execute tests in Cursor
    3. Results will be captured and validated
"""

import json
from pathlib import Path
from datetime import datetime


def generate_cursor_browser_commands():
    """
    Generate step-by-step commands for Cursor browser automation.
    
    These commands should be executed through the Cursor AI assistant
    using the MCP browser tools.
    """
    
    example_dir = Path("example_financials")
    pdf_files = list(example_dir.glob("*.pdf"))
    
    commands = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_files": len(pdf_files),
            "files": [str(f.name) for f in pdf_files]
        },
        "setup_commands": [
            {
                "step": 0,
                "description": "Verify servers are running",
                "action": "manual_check",
                "instructions": [
                    "Ensure backend server is running: python backend/main.py",
                    "Ensure frontend server is running: cd frontend && npm run dev",
                    "Backend should be on http://localhost:8000",
                    "Frontend should be on http://localhost:5173"
                ]
            }
        ],
        "test_sequences": []
    }
    
    # Generate test for each PDF
    for idx, pdf_file in enumerate(pdf_files, 1):
        # Determine doc type
        filename_lower = pdf_file.name.lower()
        if 'balance' in filename_lower or 'sheet' in filename_lower:
            doc_type = 'balance'
            doc_type_label = 'Balance Sheet'
        elif 'income' in filename_lower or 'profit' in filename_lower or 'loss' in filename_lower:
            doc_type = 'income'
            doc_type_label = 'Income Statement'
        else:
            continue
        
        test_sequence = {
            "test_id": f"test_{idx}",
            "test_name": f"Process {doc_type_label}: {pdf_file.name}",
            "file": str(pdf_file.absolute()),
            "doc_type": doc_type,
            "commands": [
                {
                    "step": 1,
                    "tool": "mcp_cursor-ide-browser_browser_navigate",
                    "params": {
                        "url": "http://localhost:5173"
                    },
                    "description": "Navigate to the application",
                    "expected": "Upload page should be visible"
                },
                {
                    "step": 2,
                    "tool": "mcp_cursor-ide-browser_browser_snapshot",
                    "params": {},
                    "description": "Capture page snapshot to identify elements",
                    "expected": "Should see upload form, file input, and doc type selector"
                },
                {
                    "step": 3,
                    "tool": "manual",
                    "description": f"Upload file: {pdf_file.name}",
                    "instructions": [
                        f"Locate the file input element",
                        f"Upload file from: {pdf_file.absolute()}",
                        "Note: File upload may require manual interaction or special handling"
                    ],
                    "expected": "File should appear in upload list"
                },
                {
                    "step": 4,
                    "tool": "mcp_cursor-ide-browser_browser_click",
                    "description": f"Select document type: {doc_type_label}",
                    "instructions": [
                        "Locate the document type selector/dropdown",
                        f"Select option: {doc_type}",
                    ],
                    "expected": f"Document type should be set to {doc_type}"
                },
                {
                    "step": 5,
                    "tool": "mcp_cursor-ide-browser_browser_click",
                    "description": "Click the submit/process button",
                    "expected": "Processing should start, spinner/progress indicator visible"
                },
                {
                    "step": 6,
                    "tool": "mcp_cursor-ide-browser_browser_wait_for",
                    "params": {
                        "time": 5
                    },
                    "description": "Wait for initial processing",
                    "expected": "Processing indicator should be active"
                },
                {
                    "step": 7,
                    "tool": "mcp_cursor-ide-browser_browser_snapshot",
                    "params": {},
                    "description": "Capture processing state",
                    "expected": "Should see processing UI with steps/progress"
                },
                {
                    "step": 8,
                    "tool": "loop",
                    "description": "Poll for completion",
                    "max_iterations": 30,
                    "iteration_delay": 2,
                    "commands": [
                        {
                            "tool": "mcp_cursor-ide-browser_browser_snapshot",
                            "description": "Check current state",
                            "check": "Look for 'Results', 'Success', or 'Error' indicators",
                            "break_condition": "Processing complete (success or error)"
                        }
                    ]
                },
                {
                    "step": 9,
                    "tool": "mcp_cursor-ide-browser_browser_snapshot",
                    "params": {},
                    "description": "Capture final results page",
                    "expected": "Should see extracted financial data in table format"
                },
                {
                    "step": 10,
                    "tool": "mcp_cursor-ide-browser_browser_take_screenshot",
                    "params": {
                        "filename": f"test_result_{idx}_{pdf_file.stem}.png",
                        "fullPage": True
                    },
                    "description": "Take screenshot of results",
                    "expected": "Full page screenshot saved"
                },
                {
                    "step": 11,
                    "tool": "validate",
                    "description": "Validate extracted data",
                    "checks": [
                        "Results table is present",
                        "Financial data is displayed",
                        "Metadata shows extraction rate",
                        "Confidence scores are visible",
                        "No error messages visible",
                        "Export options available"
                    ]
                },
                {
                    "step": 12,
                    "tool": "mcp_cursor-ide-browser_browser_click",
                    "description": "Open debug panel",
                    "instructions": "Click on debug/logs panel button",
                    "expected": "Debug panel should open"
                },
                {
                    "step": 13,
                    "tool": "mcp_cursor-ide-browser_browser_snapshot",
                    "params": {},
                    "description": "Capture debug logs",
                    "expected": "Should see processing logs, LangSmith traces, API calls"
                },
                {
                    "step": 14,
                    "tool": "extract_logs",
                    "description": "Extract and analyze logs",
                    "analysis": [
                        "Check for ERROR level logs",
                        "Verify LangChain/LangSmith traces",
                        "Look for validation errors",
                        "Check API response times",
                        "Identify any warnings or issues"
                    ]
                }
            ]
        }
        
        commands["test_sequences"].append(test_sequence)
    
    # Add batch test
    if len(pdf_files) > 1:
        batch_test = {
            "test_id": "test_batch",
            "test_name": "Batch Processing Test",
            "files": [str(f.absolute()) for f in pdf_files],
            "commands": [
                {
                    "step": 1,
                    "tool": "mcp_cursor-ide-browser_browser_navigate",
                    "params": {"url": "http://localhost:5173"},
                    "description": "Navigate to application"
                },
                {
                    "step": 2,
                    "tool": "manual",
                    "description": "Upload multiple files",
                    "instructions": [
                        f"Upload all {len(pdf_files)} PDF files",
                        "Configure doc type for each file"
                    ]
                },
                {
                    "step": 3,
                    "tool": "mcp_cursor-ide-browser_browser_click",
                    "description": "Submit batch processing"
                },
                {
                    "step": 4,
                    "tool": "monitor",
                    "description": "Monitor batch progress",
                    "expected": "Progress updates for each file"
                },
                {
                    "step": 5,
                    "tool": "mcp_cursor-ide-browser_browser_snapshot",
                    "description": "Capture batch results",
                    "expected": "List of all processed files with status"
                }
            ]
        }
        commands["test_sequences"].append(batch_test)
    
    return commands


def save_browser_test_commands():
    """Save browser test commands to file"""
    commands = generate_cursor_browser_commands()
    
    output_file = Path("test_logs") / "cursor_browser_commands.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(commands, f, indent=2)
    
    print("=" * 80)
    print("CURSOR BROWSER TEST COMMANDS GENERATED")
    print("=" * 80)
    print(f"Output file: {output_file}")
    print(f"Total test sequences: {len(commands['test_sequences'])}")
    print()
    
    # Print summary
    for test in commands["test_sequences"]:
        print(f"Test: {test['test_name']}")
        print(f"  Steps: {len(test['commands'])}")
        print(f"  File: {test.get('file', 'multiple files')}")
        print()
    
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Open the generated JSON file to see detailed commands")
    print("2. Use Cursor's AI assistant with MCP browser tools to execute tests")
    print("3. Follow each test sequence step by step")
    print("4. Capture screenshots and logs for analysis")
    print("5. Review debug panel for LangChain/LangSmith traces")
    print("=" * 80)
    
    return output_file


if __name__ == "__main__":
    save_browser_test_commands()
