"""
Test the actual spreader.py with a simple invocation to verify tracing.
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
load_dotenv()

print("=" * 60)
print("Testing Actual Spreader with LangSmith Tracing")
print("=" * 60)
print(f"LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
print(f"LANGSMITH_API_KEY: {os.getenv('LANGSMITH_API_KEY')[:20]}...")
print(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
print("=" * 60)

# Import after env is loaded
from spreader import spread_financials

# Test with one of your example files
test_file = Path("example_financials/FOMIN+LLC_Profit+and+Loss--.pdf")

if test_file.exists():
    print(f"\nProcessing test file: {test_file}")
    print("This will create a trace in LangSmith...")
    print("-" * 60)
    
    try:
        result = spread_financials(
            file_path=str(test_file),
            doc_type="income",
            period="Latest",
            max_pages=2  # Limit to 2 pages for quick test
        )
        
        print("-" * 60)
        print(f"\nSuccess! Extracted statement for period: {result.period}")
        print(f"Total Revenue: ${result.total_revenue:,.2f}")
        
        print("\n" + "=" * 60)
        print("SUCCESS! Spreader executed with tracing enabled.")
        print("Check your traces at:")
        print(f"https://smith.langchain.com")
        print(f"Project: {os.getenv('LANGSMITH_PROJECT')}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"\nTest file not found: {test_file}")
    print("Please ensure the example_financials directory exists with test PDFs.")
