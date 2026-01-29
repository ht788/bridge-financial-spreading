# JSON Viewer Feature

## Overview
Added the ability for users to view raw JSON responses in both the regular spreading view and the testing view. The JSON viewers are organized clearly to show what data corresponds to which files.

## Changes Made

### 1. New Component: `JsonViewer.tsx`
Created a reusable JSON viewer component with the following features:
- **Collapsible sections** - Click to expand/collapse JSON data
- **Copy to clipboard** - Quick copy button for each JSON section
- **Download JSON** - Download individual JSON sections as files
- **Syntax highlighting** - Clean, readable JSON formatting
- **Two variants**:
  - `JsonViewer` - Individual JSON section viewer
  - `JsonViewerContainer` - Container for multiple JSON viewers

**Location**: `frontend/src/components/JsonViewer.tsx`

### 2. Regular Spreading View (`SpreadingView.tsx`)
Added JSON viewer to the **bottom of the right panel** (after the financial table):
- **Discrete placement** - Collapsed by default, doesn't interfere with main view
- **Clear organization** - For combined extractions (auto-detect mode):
  - Income Statement JSON
  - Balance Sheet JSON  
  - Statement Detection JSON
  - Extraction Metadata
- **Single statement mode** shows:
  - Full Response JSON
  - Extraction Metadata

**Location**: `frontend/src/components/SpreadingView.tsx`

### 3. Testing View (`TestResultsComparison.tsx`)
Added JSON viewer **at the bottom of the results panel** (after field comparisons):
- **More prominent** - Testing users need easier access to raw data
- **Comprehensive data** including:
  - Complete Period Results (selected period with all field comparisons)
  - File Results (entire file with all periods)
  - Test Run Summary (overall test metrics and metadata)

**Location**: `frontend/src/components/testing/TestResultsComparison.tsx`

## How to Use

### Regular Spreading View
1. Upload and process a financial statement
2. Scroll to the bottom of the right panel (below the financial table)
3. Click "Raw Extraction Data" to expand
4. Click individual JSON sections to view:
   - Copy using the copy button
   - Download using the download button

### Testing View
1. Run a test from the Testing Lab
2. View the test results
3. Scroll to the bottom of the results panel
4. Click "Test Result Data" to expand
5. View multiple JSON sections:
   - Period-specific results
   - File-level results  
   - Test run summary

## JSON Data Structure

### Regular View - Combined Extraction (Auto Mode)
```json
{
  "income_statement": {
    "periods": [...],
    "currency": "USD",
    "scale": "thousands"
  },
  "balance_sheet": {
    "periods": [...],
    "currency": "USD",
    "scale": "thousands"
  },
  "detected_types": {
    "has_income_statement": true,
    "has_balance_sheet": true,
    "confidence": 0.95
  }
}
```

### Testing View - Test Results
```json
{
  "period_label": "FY 2023",
  "grade": "A",
  "score": 95.5,
  "field_comparisons": [
    {
      "field_name": "revenue",
      "expected_value": 1000000,
      "extracted_value": 1000000,
      "accuracy": "exact",
      "score": 1.0
    }
  ]
}
```

## Features

### Copy to Clipboard
- Click the copy icon to copy the entire JSON to clipboard
- Visual feedback with checkmark when copied
- Auto-resets after 2 seconds

### Download JSON
- Click the download icon to save JSON as a file
- Filename automatically generated from section title
- Example: `Income_Statement_JSON.json`

### Collapsible Sections
- All sections start collapsed to keep UI clean
- Click section header to expand/collapse
- Independent state for each JSON section

## Benefits

1. **Debugging** - Developers can easily inspect raw API responses
2. **Data Export** - Users can download JSON for external analysis
3. **Testing** - QA can compare expected vs actual JSON structures
4. **Documentation** - Clear view of data format for integration work
5. **Non-intrusive** - Doesn't clutter the main UI for regular users

## Testing

### To test the feature:

1. **Start the servers**:
   ```bash
   # Terminal 1 - Backend
   python -m uvicorn backend.api:app --reload --port 8000
   
   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

2. **Test Regular View**:
   - Navigate to http://localhost:5173
   - Upload a PDF financial statement
   - Choose "Auto-Detect" mode for best experience
   - After processing, scroll down in the right panel
   - Expand "Raw Extraction Data" section
   - Test copy/download features

3. **Test Testing View**:
   - Navigate to Testing Lab
   - Run a test against any company (e.g., Luminex)
   - View the test results
   - Scroll to bottom of results panel
   - Expand "Test Result Data" section
   - Verify all three JSON sections are present

## Implementation Details

### Component Architecture
```
JsonViewer.tsx
├── JsonViewer (individual section)
│   ├── Collapsible header with title
│   ├── Copy button
│   ├── Download button
│   └── JSON display area
└── JsonViewerContainer (groups multiple JsonViewers)
    ├── Collapsible container
    └── Children (JsonViewer components)
```

### State Management
- Local state for expand/collapse
- Local state for copy feedback
- No global state needed - lightweight component

### Styling
- Consistent with existing design system
- Uses Tailwind CSS classes
- Lucide React icons for UI elements
- Responsive layout

## Future Enhancements

Possible improvements:
1. Syntax highlighting with color-coded JSON
2. Search/filter within JSON
3. Diff view for comparing two JSON objects
4. Share JSON via URL or API
5. JSON validation and schema display
