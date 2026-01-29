# Luminex (Candle-Lite) Test Case

## Overview

**Company:** Candle-Lite (Luminex)  
**Test ID:** `luminex`  
**Document Types:** Income Statement (multi-period) + Balance Sheet  
**File Format:** Excel (.xlsx)  
**Periods Covered:** 
- Income Statement: FY2023, FY2024, FY2025
- Balance Sheet: FY2025 only

## Test Files

Both statements are in the same Excel file with different sheets:

1. **Income Statement**
   - **Filename:** `Luminex/2025-11-30 Candle-Lite Interim Financial Statements.xlsx`
   - **Sheet:** "FY26 P&L Actuals"
   - **Periods:** FY2023, FY2024, FY2025 (3 comparative fiscal years)
   
2. **Balance Sheet**
   - **Filename:** `Luminex/2025-11-30 Candle-Lite Interim Financial Statements.xlsx`
   - **Sheet:** "Sch 6 - FY26 BS Actuals"
   - **Period:** FY2025 fiscal year-end (Feb 28, 2025)

- **Location:** `example_financials/Luminex/`

## Answer Key Structure

The answer key for Luminex (`luminex_answer_key.json`) contains:
- **File 1:** Income statement with 3 fiscal periods
- **File 2:** Balance sheet with 1 period (FY2025)

### FY2025 (Period ending 2025-02-28)

| Field | Value | Notes |
|-------|--------|-------|
| Revenue | $191,939 | Net sales |
| COGS | $127,810 | Cost of goods sold |
| Gross Profit | $64,129 | |
| SG&A | $55,264 | Operating expenses less D&A |
| D&A | $5,855 | From cash flow statement |
| Operating Income | $3,010 | Income from operations |
| Interest Expense | $11,832 | Net interest expense |
| Other Income/Expense | ($476) | FX loss + other expense |
| Pre-tax Income | ($9,289) | Loss before tax |
| Income Tax Expense | $283 | |
| Net Income | ($9,581) | Net loss |

### FY2024 (Period ending 2024-02-29)

| Field | Value | Notes |
|-------|--------|-------|
| Revenue | $225,747 | Net sales |
| COGS | $154,541 | Cost of goods sold |
| Gross Profit | $71,206 | |
| SG&A | $64,360 | Operating expenses less D&A |
| D&A | $6,650 | From cash flow statement |
| Operating Income | $196 | Income from operations |
| Interest Expense | $10,240 | Net interest expense |
| Other Income/Expense | ($15) | FX gain + other expense |
| Pre-tax Income | ($10,059) | Loss before tax |
| Income Tax Expense | $885 | |
| Net Income | ($10,944) | Net loss |

### FY2023 (Period ending 2023-02-28)

| Field | Value | Notes |
|-------|--------|-------|
| Revenue | $234,249 | Net sales |
| COGS | $178,834 | Cost of goods sold |
| Gross Profit | $55,415 | |
| SG&A | $70,988 | Operating expenses less D&A |
| D&A | $7,112 | From cash flow statement |
| Operating Income | ($22,685) | Loss from operations |
| Interest Expense | $8,786 | Interest expense |
| Other Income/Expense | ($348) | FX loss + other expense |
| Pre-tax Income | ($31,819) | Loss before tax |
| Income Tax Expense | $904 | |
| Net Income | ($32,723) | Net loss |

### Balance Sheet - FY2025 (As of 2025-02-28)

| Field | Value | Notes |
|-------|--------|-------|
| Cash & Equivalents | $1,398 | Cash |
| Accounts Receivable | $10,549 | Net of allowances |
| Inventory | $41,816 | Net of reserves |
| Total Current Assets | $57,753 | |
| Net PP&E | $16,544 | Including ROU assets |
| Goodwill & Intangibles | $928 | Intangible assets |
| Total Assets | $89,535 | |
| Accounts Payable | $19,252 | Trade payables |
| Total Current Liabilities | $28,399 | |
| Long-term Debt | $84,913 | Various debt facilities |
| Total Liabilities | $127,887 | |
| Total Shareholders' Equity | ($38,352) | Negative equity |
| Total Liabilities & Equity | $89,535 | Balanced |

## Key Characteristics

1. **Multi-Sheet Excel File:** Income statement and balance sheet in different sheets
2. **Multi-Period Income Statement:** 3 fiscal years in one sheet
3. **Single-Period Balance Sheet:** Only FY2025 fiscal year-end available
2. **Scale:** All values in thousands USD
3. **D&A Treatment:** Depreciation & Amortization is embedded in operating expenses on the income statement face, but broken out separately in the cash flow statement
4. **Interest Presentation:** Interest expense is shown net of interest income
5. **Fiscal Year End:** Company has a February fiscal year end (FY2025 = period ending Feb 28, 2025)
6. **Negative Equity:** Balance sheet shows significant negative shareholders' equity due to accumulated losses
7. **Excel Format:** First test case using .xlsx format (all others are PDFs)

## Testing Configuration

The test case is configured in `test_runner.py` as:

```python
TestCompany(
    id="luminex",
    name="Candle-Lite (Luminex)",
    files=[
        TestFile(
            filename="Luminex/2025-11-30 Candle-Lite Interim Financial Statements.xlsx", 
            doc_type="income", 
            period="FY2023-FY2025",
            description="Interim Financial Statements with FY2023, FY2024, and FY2025 comparative P&L periods"
        ),
        TestFile(
            filename="Luminex/2025-11-30 Candle-Lite Interim Financial Statements.xlsx", 
            doc_type="balance", 
            period="FY2025",
            description="Balance Sheet as of Feb 28, 2025 (FY2025 fiscal year-end)"
        ),
    ],
    answer_key_path="luminex_answer_key.json"
)
```

## Expected Test Behavior

When running this test:
1. The spreader should process the Excel file twice (once for income, once for balance)
2. **Income Statement:** Extract three distinct fiscal periods (FY2023, FY2024, FY2025)
3. **Balance Sheet:** Extract one fiscal year-end snapshot (FY2025 as of Feb 28, 2025)
4. For each period, extract the appropriate line items
5. The grading system will compare extracted values against the answer key
6. Tolerance is set to 5% for most fields, 10% for other income/expense

## Usage

To run this test case via the API:

```bash
POST /api/testing/run
{
  "company_id": "luminex",
  "model_name": "gpt-4o",
  "tolerance_percent": 5.0,
  "extended_thinking": false
}
```

Or via the web UI Testing Lab, select "Candle-Lite (Luminex)" from the company dropdown.

## Notes

- This is the first Excel-based test case in the suite
- The same file contains both income statement and balance sheet in different sheets
- The file structure requires proper subdirectory handling (`Luminex/` folder)
- Period labels use "FY" prefix format (FY2023, FY2024, FY2025)
- All three income statement periods show net losses, making this a good test for negative number handling
- Balance sheet has negative equity, testing handling of distressed company financials
- Balance sheet only has FY2025 (no historical comparatives available in the file)
