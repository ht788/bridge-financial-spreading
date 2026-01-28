"""
Quick test to verify multi-period extraction works correctly.
"""

import json
from pathlib import Path
from spreader import spread_financials

# Test with the example income statement
pdf_path = Path("example_financials/FOMIN+LLC_Profit+and+Loss--.pdf")

if not pdf_path.exists():
    print(f"Error: {pdf_path} not found")
    exit(1)

print("=" * 70)
print("Testing Multi-Period Extraction")
print("=" * 70)
print(f"\nFile: {pdf_path.name}")
print("Doc Type: income")
print("Mode: Multi-Period (all periods detected)\n")

try:
    # Spread with multi-period enabled
    result = spread_financials(
        file_path=str(pdf_path),
        doc_type="income",
        multi_period=True,
        max_pages=5,
        dpi=200
    )
    
    # Check if it's multi-period
    if hasattr(result, 'periods'):
        print(f"✅ Multi-period result returned")
        print(f"   Number of periods: {len(result.periods)}")
        print(f"   Currency: {result.currency}")
        print(f"   Scale: {result.scale}\n")
        
        print("Period Details:")
        for i, period in enumerate(result.periods, 1):
            print(f"\n  Period {i}:")
            print(f"    Label: {period.period_label}")
            print(f"    End Date: {period.end_date or 'N/A'}")
            
            # Show a few key line items
            data = period.data
            if hasattr(data, 'revenue') and data.revenue.value:
                print(f"    Revenue: {data.revenue.value:,.2f}")
            if hasattr(data, 'net_income') and data.net_income.value:
                print(f"    Net Income: {data.net_income.value:,.2f}")
        
        # Save to JSON for inspection
        output_file = "test_multi_period_output.json"
        with open(output_file, 'w') as f:
            json.dump(result.model_dump(), f, indent=2)
        print(f"\n✅ Full results saved to: {output_file}")
        
    else:
        print("❌ Single-period result returned (expected multi-period)")
        print(f"   Type: {type(result).__name__}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
