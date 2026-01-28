"""
Test script to demonstrate financial spreading with the example PDFs.
This uses the backend API to process the example financials.
"""

import requests
import json
import os
from pathlib import Path

# Configuration
BACKEND_URL = "http://localhost:8000"
EXAMPLE_DIR = Path("example_financials")

def test_spread_document(pdf_path: str, doc_type: str, period: str = "FY2023"):
    """Test spreading a financial document"""
    
    print(f"\n{'='*70}")
    print(f"Testing: {pdf_path}")
    print(f"Type: {doc_type}")
    print(f"Period: {period}")
    print(f"{'='*70}\n")
    
    # Prepare the file
    with open(pdf_path, 'rb') as f:
        files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
        data = {
            'doc_type': doc_type,
            'period': period,
            'max_pages': 10,
            'dpi': 200
            # Note: Prompts are loaded from LangSmith Hub (no fallback)
        }
        
        print("Sending request to API...")
        try:
            response = requests.post(f"{BACKEND_URL}/api/spread", files=files, data=data)
            
            if response.status_code == 200:
                result = response.json()
                
                print("[SUCCESS]\n")
                
                # Display metadata
                if 'metadata' in result:
                    meta = result['metadata']
                    print("Extraction Metadata:")
                    print(f"  - Total Fields: {meta.get('total_fields', 'N/A')}")
                    print(f"  - High Confidence: {meta.get('high_confidence', 'N/A')}")
                    print(f"  - Medium Confidence: {meta.get('medium_confidence', 'N/A')}")
                    print(f"  - Low Confidence: {meta.get('low_confidence', 'N/A')}")
                    print(f"  - Average Confidence: {meta.get('average_confidence', 0)*100:.1f}%")
                    print(f"  - Extraction Rate: {meta.get('extraction_rate', 0)*100:.1f}%\n")
                
                # Display extracted data
                if 'data' in result:
                    print("Extracted Financial Data:")
                    print(json.dumps(result['data'], indent=2))
                    
                # Save to file
                output_file = f"test_output_{doc_type}_{os.path.basename(pdf_path)}.json"
                with open(output_file, 'w') as out:
                    json.dump(result, out, indent=2)
                print(f"\nFull results saved to: {output_file}")
                
            else:
                print(f"[ERROR]: {response.status_code}")
                print(response.text)
                
        except requests.exceptions.ConnectionError:
            print("[ERROR]: Cannot connect to backend server!")
            print("   Make sure the backend is running on http://localhost:8000")
            print("   Run: python backend/main.py")
        except Exception as e:
            print(f"[ERROR]: {e}")

def main():
    """Main test function"""
    
    print("="*70)
    print("Bridge Financial Spreader - Test Suite")
    print("="*70)
    
    # Check if backend is running
    try:
        response = requests.get(f"{BACKEND_URL}/docs")
        print("[OK] Backend server is running!")
    except:
        print("[ERROR] Backend server is NOT running!")
        print("   Please start it with: python backend/main.py")
        return
    
    # Find example PDFs
    if not EXAMPLE_DIR.exists():
        print(f"[ERROR] Example directory not found: {EXAMPLE_DIR}")
        return
    
    pdfs = list(EXAMPLE_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"[ERROR] No PDF files found in {EXAMPLE_DIR}")
        return
    
    print(f"\nFound {len(pdfs)} example PDF(s):\n")
    for pdf in pdfs:
        print(f"  - {pdf.name}")
    
    # Test each PDF
    for pdf in pdfs:
        filename_lower = pdf.name.lower()
        
        # Determine document type from filename
        if 'balance' in filename_lower or 'sheet' in filename_lower:
            doc_type = 'balance'
        elif 'income' in filename_lower or 'profit' in filename_lower or 'loss' in filename_lower:
            doc_type = 'income'
        else:
            print(f"\n[WARNING] Skipping {pdf.name} - cannot determine type from filename")
            continue
        
        test_spread_document(str(pdf), doc_type, "FY2023")
    
    print("\n" + "="*70)
    print("Testing Complete!")
    print("="*70)

if __name__ == "__main__":
    main()
