#!/usr/bin/env python3
"""
Test script for combined financial extraction with auto-detection.

This script tests the new auto-detect functionality that:
1. Automatically detects which statement types are present in a PDF
2. Runs parallel extraction when both income statement and balance sheet are found
3. Returns combined results

Usage:
    python test_combined_extraction.py [path_to_pdf]
    
If no path is provided, it will look for example PDFs in example_financials/
"""

import asyncio
import sys
import os
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from spreader import (
    spread_pdf_combined,
    spread_financials,
    _detect_statement_types,
    _convert_pdf_to_images,
    get_model_config_from_environment,
)
from models import CombinedFinancialExtraction


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_detection_results(detection):
    """Print statement type detection results."""
    print(f"  Has Income Statement: {detection.has_income_statement}")
    print(f"  Has Balance Sheet: {detection.has_balance_sheet}")
    print(f"  Overall Confidence: {detection.confidence:.2%}")
    
    if detection.income_statement_pages:
        print(f"  Income Statement Pages: {detection.income_statement_pages}")
        print(f"  Income Statement Confidence: {detection.income_statement_confidence:.2%}")
    
    if detection.balance_sheet_pages:
        print(f"  Balance Sheet Pages: {detection.balance_sheet_pages}")
        print(f"  Balance Sheet Confidence: {detection.balance_sheet_confidence:.2%}")
    
    if detection.notes:
        print(f"  Notes: {detection.notes}")


def print_combined_results(result: CombinedFinancialExtraction):
    """Print combined extraction results."""
    print_section("Combined Extraction Results")
    
    # Detection results
    print("\nDetection Results:")
    print_detection_results(result.detected_types)
    
    # Income statement results
    if result.income_statement:
        print(f"\nIncome Statement: {len(result.income_statement.periods)} period(s)")
        for period in result.income_statement.periods:
            print(f"  - {period.period_label}")
            if period.data.revenue.value:
                print(f"    Revenue: ${period.data.revenue.value:,.2f}")
            if period.data.net_income.value:
                print(f"    Net Income: ${period.data.net_income.value:,.2f}")
    else:
        print("\nIncome Statement: Not found")
    
    # Balance sheet results
    if result.balance_sheet:
        print(f"\nBalance Sheet: {len(result.balance_sheet.periods)} period(s)")
        for period in result.balance_sheet.periods:
            print(f"  - {period.period_label}")
            if period.data.total_assets.value:
                print(f"    Total Assets: ${period.data.total_assets.value:,.2f}")
            if period.data.total_liabilities_and_equity.value:
                print(f"    Total L&E: ${period.data.total_liabilities_and_equity.value:,.2f}")
    else:
        print("\nBalance Sheet: Not found")
    
    # Metadata
    print("\nExtraction Metadata:")
    meta = result.extraction_metadata
    print(f"  Execution Time: {meta.get('execution_time_seconds', 0):.2f}s")
    print(f"  Model: {meta.get('model', 'unknown')}")
    print(f"  Parallel Extraction: {meta.get('parallel_extraction', False)}")
    print(f"  Pages Processed: {meta.get('pages_processed', 0)}")


async def test_detection_only(pdf_path: str):
    """Test only the statement type detection."""
    print_section("Testing Statement Type Detection")
    print(f"  PDF: {pdf_path}")
    
    # Get model config
    model_name, model_kwargs = get_model_config_from_environment()
    print(f"  Model: {model_name}")
    
    # Convert PDF to images
    print("\n  Converting PDF to images...")
    images = _convert_pdf_to_images(pdf_path, dpi=200, max_pages=None)
    print(f"  Converted {len(images)} pages")
    
    # Detect statement types
    print("\n  Detecting statement types...")
    detection = _detect_statement_types(
        base64_images=images,
        model_name=model_name,
        model_kwargs=model_kwargs,
    )
    
    print("\nDetection Results:")
    print_detection_results(detection)
    
    return detection


async def test_combined_extraction(pdf_path: str):
    """Test the full combined extraction."""
    print_section("Testing Combined Extraction (Auto-Detect + Parallel)")
    print(f"  PDF: {pdf_path}")
    
    start_time = time.time()
    
    # Run combined extraction
    result = await spread_pdf_combined(
        pdf_path=pdf_path,
        dpi=200,
    )
    
    elapsed = time.time() - start_time
    print(f"\n  Total execution time: {elapsed:.2f}s")
    
    # Print results
    print_combined_results(result)
    
    return result


def test_spread_financials_auto(pdf_path: str):
    """Test spread_financials with doc_type='auto'."""
    print_section("Testing spread_financials(doc_type='auto')")
    print(f"  PDF: {pdf_path}")
    
    start_time = time.time()
    
    # Run via spread_financials
    result = spread_financials(
        file_path=pdf_path,
        doc_type="auto",
    )
    
    elapsed = time.time() - start_time
    print(f"\n  Total execution time: {elapsed:.2f}s")
    
    # Print results
    if isinstance(result, CombinedFinancialExtraction):
        print_combined_results(result)
    else:
        print(f"\n  Result type: {type(result).__name__}")
    
    return result


async def main():
    """Main test function."""
    print("\n" + "=" * 60)
    print("  Combined Financial Extraction Test")
    print("=" * 60)
    
    # Get PDF path from command line or use defaults
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        # Look for example PDFs
        example_dir = Path(__file__).parent / "example_financials"
        pdfs = list(example_dir.glob("*.pdf")) if example_dir.exists() else []
        
        if pdfs:
            pdf_path = str(pdfs[0])
            print(f"\nUsing example PDF: {pdf_path}")
        else:
            print("\nNo PDF path provided and no example PDFs found.")
            print("Usage: python test_combined_extraction.py <path_to_pdf>")
            print("\nExample PDFs that work well with this test:")
            print("  - 2024_Q4_pNeo_Consolidated_Financial_Reports.pdf")
            print("  - FY_2023_pNeo_Financial_Packet.pdf")
            return
    
    # Verify file exists
    if not Path(pdf_path).exists():
        print(f"\nError: File not found: {pdf_path}")
        return
    
    # Run tests
    try:
        # Test 1: Detection only
        detection = await test_detection_only(pdf_path)
        
        # Test 2: Full combined extraction (if both types detected)
        if detection.has_income_statement and detection.has_balance_sheet:
            print("\n\n*** Both statement types detected - testing parallel extraction ***")
            result = await test_combined_extraction(pdf_path)
        else:
            print("\n\n*** Only one statement type detected - testing single extraction ***")
            result = await test_combined_extraction(pdf_path)
        
        # Test 3: Via spread_financials interface
        print("\n\n*** Testing via spread_financials(doc_type='auto') ***")
        test_spread_financials_auto(pdf_path)
        
        print_section("All Tests Completed Successfully!")
        
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code or 0)
