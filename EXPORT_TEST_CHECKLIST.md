# Export Functionality Test Checklist

Use this checklist to verify that all export functionality is working correctly after the fixes.

---

## ✅ Test 1: Single-Period Income Statement Export

**Setup:**
1. Upload a PDF with a single period income statement
2. Set `doc_type` to `income`

**JSON Export Test:**
- [ ] Click Export → Export as JSON
- [ ] Verify filename: `{filename}_income_statement.json`
- [ ] Open the JSON file
- [ ] Verify structure contains `{ data: {...}, metadata: {...} }`
- [ ] Verify `data` contains income statement fields (revenue, cogs, etc.)
- [ ] Verify `metadata` contains extraction stats

**CSV Export Test:**
- [ ] Click Export → Export as CSV
- [ ] Verify filename: `{filename}_income_statement.csv`
- [ ] Open the CSV file in Excel/Sheets
- [ ] Verify columns: `Field, Value, Confidence, Raw Fields Used, Source Section`
- [ ] Verify all income statement line items are present
- [ ] Verify values match what's shown in the UI

---

## ✅ Test 2: Multi-Period Balance Sheet Export

**Setup:**
1. Upload a PDF with multiple periods (e.g., 3 years)
2. Set `doc_type` to `balance`

**JSON Export Test:**
- [ ] Click Export → Export as JSON
- [ ] Verify filename: `{filename}_balance_statement.json`
- [ ] Open the JSON file
- [ ] Verify structure contains `{ data: { periods: [...] }, metadata: {...} }`
- [ ] Verify `periods` array has correct number of periods
- [ ] Verify each period has `period_label`, `end_date`, `data`, etc.

**CSV Export Test:**
- [ ] Click Export → Export as CSV
- [ ] Verify filename: `{filename}_balance_statement.csv`
- [ ] Open the CSV file in Excel/Sheets
- [ ] Verify header: `Field, {Period1} Value, {Period1} Confidence, ..., {Period2} Value, ...`
- [ ] Verify all periods are shown side-by-side
- [ ] Verify values match what's shown in the UI
- [ ] Check that all balance sheet items are present (assets, liabilities, equity)

---

## ✅ Test 3: Combined Auto-Detect Export (CRITICAL TEST)

**Setup:**
1. Upload a PDF that contains BOTH income statement and balance sheet
2. Set `doc_type` to `auto`
3. Wait for extraction to complete
4. Verify both tabs appear (Income Statement and Balance Sheet)

**JSON Export Test - FROM INCOME STATEMENT TAB:**
- [ ] Click on Income Statement tab
- [ ] Click Export → Export as JSON
- [ ] Verify description shows "Both statements included"
- [ ] Verify filename: `{filename}_combined_statements.json`
- [ ] Open the JSON file
- [ ] **CRITICAL:** Verify structure contains BOTH statements:
  ```json
  {
    "data": {
      "income_statement": { "periods": [...] },
      "balance_sheet": { "periods": [...] },
      "detected_types": { ... },
      "extraction_metadata": { ... }
    },
    "metadata": { ... }
  }
  ```
- [ ] Verify both `income_statement` and `balance_sheet` are populated
- [ ] Verify `detected_types` shows correct detection info

**JSON Export Test - FROM BALANCE SHEET TAB:**
- [ ] Switch to Balance Sheet tab
- [ ] Click Export → Export as JSON
- [ ] Verify filename: `{filename}_combined_statements.json`
- [ ] Open the JSON file
- [ ] **CRITICAL:** Verify BOTH statements are still in the export (same as above)
- [ ] This confirms we're not just exporting the active tab anymore

**CSV Export Test:**
- [ ] From either tab, click Export → Export as CSV
- [ ] Verify description shows "Creates 2 files (IS + BS)"
- [ ] **CRITICAL:** Verify TWO CSV files are downloaded:
  - [ ] `{filename}_income_statement.csv`
  - [ ] `{filename}_balance_sheet.csv`
- [ ] Open the income statement CSV:
  - [ ] Verify multi-period format with all periods side-by-side
  - [ ] Verify all income statement line items present
- [ ] Open the balance sheet CSV:
  - [ ] Verify multi-period format with all periods side-by-side
  - [ ] Verify all balance sheet line items present

---

## ✅ Test 4: Combined Export with Missing Statement

**Setup:**
1. Upload a PDF that only has an Income Statement (no Balance Sheet)
2. Set `doc_type` to `auto`

**JSON Export Test:**
- [ ] Click Export → Export as JSON
- [ ] Open the JSON file
- [ ] Verify `income_statement` is populated
- [ ] Verify `balance_sheet` is `null` or empty
- [ ] Verify `detected_types.has_income_statement` is `true`
- [ ] Verify `detected_types.has_balance_sheet` is `false`

**CSV Export Test:**
- [ ] Click Export → Export as CSV
- [ ] Verify only ONE CSV file is created: `{filename}_income_statement.csv`
- [ ] No error should occur
- [ ] No empty balance sheet CSV should be created

---

## ✅ Test 5: Edge Cases

**Test 5a: Empty Periods**
- [ ] Upload a PDF where extraction finds no data
- [ ] Verify export doesn't crash
- [ ] Verify empty/null values are handled gracefully

**Test 5b: Special Characters in Filename**
- [ ] Upload a PDF with special characters in name (e.g., "Q1-2024 (Final).pdf")
- [ ] Verify exported filenames are valid
- [ ] Verify files download successfully

**Test 5c: Large Multi-Period Dataset**
- [ ] Upload a PDF with 5+ periods
- [ ] Verify CSV export handles many columns correctly
- [ ] Verify CSV opens properly in Excel without truncation

---

## Expected Behavior Summary

| Mode | JSON Export | CSV Export |
|------|-------------|------------|
| Single-period IS/BS | Single file with one statement | Single CSV file |
| Multi-period IS/BS | Single file with periods array | Single CSV with side-by-side periods |
| **Combined (auto)** | **Single file with BOTH statements** | **TWO CSV files (one for IS, one for BS)** |

---

## Common Issues to Watch For

❌ **OLD BUG:** In auto-detect mode, JSON export only contained the active tab's data  
✅ **FIXED:** JSON export now contains full `CombinedFinancialExtraction` with both statements

❌ **OLD BUG:** In auto-detect mode, CSV export would fail or export incorrectly  
✅ **FIXED:** CSV export now creates two separate properly-formatted CSV files

❌ **OLD BUG:** Export menu didn't indicate combined export behavior  
✅ **FIXED:** Menu descriptions now show "Both statements included" and "Creates 2 files (IS + BS)"

---

## Success Criteria

All tests pass when:
- ✅ Single-period exports work correctly (no regression)
- ✅ Multi-period exports work correctly (no regression)
- ✅ **Combined JSON exports contain BOTH statements**
- ✅ **Combined CSV exports create TWO separate files**
- ✅ No data is lost during export
- ✅ Export UI clearly indicates what will be exported
- ✅ No errors or crashes during any export operation

---

## Report Issues

If any test fails, note:
1. Which test case failed
2. What doc_type was used
3. Expected behavior vs. actual behavior
4. Any error messages in browser console
5. Screenshot of the issue if applicable
