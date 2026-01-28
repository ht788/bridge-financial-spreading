#!/usr/bin/env python3
"""
Quick Test Runner
=================

This script helps you quickly run tests with proper setup.
It checks prerequisites and guides you through the testing process.
"""

import subprocess
import sys
import os
import time
from pathlib import Path
import urllib.request
import urllib.error


def check_backend():
    """Check if backend is running"""
    try:
        response = urllib.request.urlopen('http://localhost:8000/api/health', timeout=2)
        if response.getcode() == 200:
            print("[OK] Backend is running on http://localhost:8000")
            return True
    except:
        pass
    
    print("[FAIL] Backend is NOT running on http://localhost:8000")
    return False


def check_frontend():
    """Check if frontend is running"""
    try:
        response = urllib.request.urlopen('http://localhost:5173', timeout=2)
        if response.getcode() == 200:
            print("[OK] Frontend is running on http://localhost:5173")
            return True
    except:
        pass
    
    print("[FAIL] Frontend is NOT running on http://localhost:5173")
    return False


def check_example_files():
    """Check if example PDFs exist"""
    example_dir = Path("example_financials")
    if not example_dir.exists():
        print(f"[FAIL] Example directory not found: {example_dir}")
        return False
    
    pdfs = list(example_dir.glob("*.pdf"))
    if not pdfs:
        print(f"[FAIL] No PDF files found in {example_dir}")
        return False
    
    print(f"[OK] Found {len(pdfs)} PDF file(s) in {example_dir}")
    for pdf in pdfs:
        print(f"     - {pdf.name}")
    return True


def check_env():
    """Check if .env file exists and has keys"""
    env_file = Path(".env")
    if not env_file.exists():
        print("[WARN] .env file not found - API keys may not be configured")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
        
    has_openai = 'OPENAI_API_KEY=' in content
    has_langsmith = 'LANGSMITH_API_KEY=' in content
    
    if has_openai and has_langsmith:
        print("[OK] .env file exists with API keys")
        return True
    else:
        print("[WARN] .env file exists but may be missing API keys")
        if not has_openai:
            print("     - OPENAI_API_KEY not found")
        if not has_langsmith:
            print("     - LANGSMITH_API_KEY not found")
        return False


def main():
    print("="*80)
    print("FINANCIAL SPREADING - QUICK TEST RUNNER")
    print("="*80)
    print()
    
    print("Checking prerequisites...")
    print()
    
    # Check environment
    env_ok = check_env()
    
    # Check example files
    files_ok = check_example_files()
    
    # Check servers
    backend_ok = check_backend()
    frontend_ok = check_frontend()
    
    print()
    print("="*80)
    print("PREREQUISITES CHECK COMPLETE")
    print("="*80)
    print()
    
    if not files_ok:
        print("ERROR: Example files are missing. Cannot run tests.")
        return 1
    
    if not backend_ok:
        print("Backend is not running. You need to start it first.")
        print()
        print("In a separate terminal, run:")
        print("  python backend/main.py")
        print()
        choice = input("Do you want to start the backend now? (y/n): ").strip().lower()
        if choice == 'y':
            print("\nStarting backend server...")
            print("(This will run in the background - check for errors)")
            print()
            # Note: We don't actually start it here because it needs to run in a separate terminal
            print("Please start the backend in another terminal and run this script again.")
            return 1
    
    if not frontend_ok:
        print("\nWARNING: Frontend is not running.")
        print("Browser tests will not work without the frontend.")
        print()
        print("In a separate terminal, run:")
        print("  cd frontend")
        print("  npm run dev")
        print()
    
    if not env_ok:
        print("\nWARNING: API keys may not be configured.")
        print("Tests might fail without proper API keys in .env file.")
        print()
    
    if backend_ok:
        print("="*80)
        print("READY TO RUN TESTS")
        print("="*80)
        print()
        print("Choose a test to run:")
        print()
        print("1. API Tests (recommended first)")
        print("   - Tests backend endpoints directly")
        print("   - Processes example PDFs")
        print("   - Generates debug logs")
        print()
        print("2. Browser Test Guide")
        print("   - Opens interactive browser testing guide")
        print("   - Use with Cursor AI assistant")
        print()
        print("3. View Testing Documentation")
        print("   - Opens README_TESTING.md")
        print()
        print("4. Exit")
        print()
        
        choice = input("Enter your choice (1-4): ").strip()
        
        if choice == '1':
            print("\nRunning API tests...")
            print("="*80)
            print()
            result = subprocess.run([sys.executable, "test_browser_automation.py"])
            return result.returncode
            
        elif choice == '2':
            print("\nOpening browser test guide...")
            print("="*80)
            print()
            result = subprocess.run([sys.executable, "test_browser_live.py"])
            return result.returncode
            
        elif choice == '3':
            readme = Path("README_TESTING.md")
            if readme.exists():
                with open(readme, 'r', encoding='utf-8') as f:
                    print(f.read())
            else:
                print("README_TESTING.md not found")
            return 0
            
        elif choice == '4':
            print("\nExiting...")
            return 0
            
        else:
            print("\nInvalid choice")
            return 1
    
    return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nERROR: {e}")
        sys.exit(1)
