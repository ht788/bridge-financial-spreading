# Visual Guide: In-Progress Test Tracking

## Before vs. After

### Before Implementation
```
Test History Table:
┌──────────┬──────────┬────────┬───────┬───────┬───────┬──────────┬─────────┐
│ Date/Time│ Company  │ Model  │ Grade │ Score │ Files │ Duration │ Actions │
├──────────┼──────────┼────────┼───────┼───────┼───────┼──────────┼─────────┤
│ 1/29 2PM │ LKC      │ Opus   │  A+   │ 96.3% │   8   │  2m 15s  │  View   │
│ 1/29 1PM │ FOMIN    │ Sonnet │  B    │ 82.1% │   2   │    45s   │  View   │
└──────────┴──────────┴────────┴───────┴───────┴───────┴──────────┴─────────┘

Issues:
- No visibility when a test is running
- No way to know if a test started successfully
- Can't see running tests in other tabs/sessions
```

### After Implementation
```
Test History Table:
┌──────────┬──────────┬────────┬──────────┬───────┬───────┬───────┬──────────┬─────────┐
│ Date/Time│ Company  │ Model  │  Status  │ Grade │ Score │ Files │ Duration │ Actions │
├──────────┼──────────┼────────┼──────────┼───────┼───────┼───────┼──────────┼─────────┤
│ 1/29 2PM │ Luminex  │ Opus   │ Running  │  —    │   —   │   8   │ Running… │In progress│
│          │          │        │  (spin)  │       │       │       │          │         │
│ 1/29 2PM │ LKC      │ Opus   │Complete  │  A+   │ 96.3% │   8   │  2m 15s  │  View   │
│ 1/29 1PM │ FOMIN    │ Sonnet │Complete  │  B    │ 82.1% │   2   │    45s   │  View   │
│ 1/29 1PM │ pNeo     │ Sonnet │  Error   │   F   │  0.0% │   4   │    12s   │  View   │
└──────────┴──────────┴────────┴──────────┴───────┴───────┴───────┴──────────┴─────────┘

Benefits:
✓ Instant visibility when test starts
✓ Clear status indicators with appropriate colors
✓ Auto-refreshes while tests are running
✓ Works across multiple tabs/users
```

## Status Badge Colors

```
┌─────────────┬────────────────┬─────────────────────┐
│   Status    │     Color      │      Behavior       │
├─────────────┼────────────────┼─────────────────────┤
│  Pending    │  Gray          │  Static             │
│  Running    │  Blue          │  Animated spinner   │
│  Complete   │  Green         │  Static             │
│  Error      │  Red           │  Static             │
└─────────────┴────────────────┴─────────────────────┘
```

## Running Test Indicators

When a test is running, the table shows:

```
Status Column:     [🔄] Running    (Blue badge with spinning loader)
Grade Column:      In progress...  (Gray placeholder text)
Score Column:      —               (Em dash)
Duration Column:   Running...      (Gray italic text)
Actions Column:    In progress     (Disabled, gray italic)
```

## Auto-Refresh Behavior

```
┌─────────────────────────────────────┐
│  History Table                      │
│  ┌───────────────────────────────┐  │
│  │ Test 1: Running    [Auto-     │  │ ← Refreshes every 3s
│  │ Test 2: Complete   refreshing]│  │   while running tests
│  │ Test 3: Complete              │  │   are present
│  └───────────────────────────────┘  │
│                                     │
│  When test completes:               │
│  ┌───────────────────────────────┐  │
│  │ Test 1: Complete   [Stopped]  │  │ ← Auto-refresh stops
│  │ Test 2: Complete              │  │   when no running
│  │ Test 3: Complete              │  │   tests detected
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Database Schema

```sql
-- New column added to test_runs table:
ALTER TABLE test_runs ADD COLUMN status TEXT NOT NULL DEFAULT 'pending';

-- Possible values:
-- 'pending'  - Test created but not started yet
-- 'running'  - Test currently executing
-- 'complete' - Test finished successfully
-- 'error'    - Test failed with error

-- Migration handles existing records:
-- Existing records automatically get 'complete' status
```

## Test Lifecycle

```
User clicks "Run Test"
         ↓
    [pending]  ← Record created instantly
         ↓
   save_test_result() saves with status='running'
         ↓
    [running]  ← Visible in history table (animated)
         ↓
    ... Test executes (extracts files, grades, etc.) ...
         ↓
    All files processed
         ↓
    [complete] ← Final status update
    or
    [error]    ← If something failed
         ↓
    Results viewable via "View" button
```

## Code Flow

### Backend (test_runner.py)
```python
async def run_test(config: TestRunConfig):
    test_id = str(uuid.uuid4())
    
    # 1. Create initial record immediately
    initial_result = TestRunResult(
        id=test_id,
        status=TestRunStatus.RUNNING,  # ← Key change
        overall_score=0.0,
        ...
    )
    save_test_result(initial_result)  # Visible immediately!
    
    # 2. Run the actual test
    ... process files ...
    
    # 3. Update with final results
    final_result.status = TestRunStatus.COMPLETE
    save_test_result(final_result)  # Updates existing record
```

### Frontend (TestingPage.tsx)
```typescript
const loadHistory = async () => {
    const response = await testingApi.getHistory();
    setHistory(response.runs);
    
    // Check if any tests are still running
    const hasRunningTests = response.runs.some(
        run => run.status === 'running'
    );
    
    // Set up auto-refresh if needed
    if (hasRunningTests) {
        historyRefreshInterval = setInterval(
            loadHistory,
            3000  // Refresh every 3 seconds
        );
    } else {
        clearInterval(historyRefreshInterval);
    }
};
```

### Frontend (TestHistoryTable.tsx)
```tsx
{run.status === 'running' ? (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 
                     text-xs font-semibold rounded-lg border 
                     text-blue-600 bg-blue-50 border-blue-200">
        <Loader2 className="w-3 h-3 animate-spin" />
        Running
    </span>
) : (
    <span className={`... ${getStatusColor(run.status)}`}>
        {getStatusLabel(run.status)}
    </span>
)}
```

## Example Usage

### Scenario: User runs a test

1. **T=0s** - User clicks "Run Test" on Luminex company
2. **T=0.1s** - Backend saves initial record with status='running'
3. **T=0.2s** - Frontend shows test in history with blue "Running" badge
4. **T=3s** - Auto-refresh updates (still running)
5. **T=6s** - Auto-refresh updates (still running)
6. **T=125s** - Test completes, status updated to 'complete'
7. **T=126s** - Auto-refresh updates, shows green "Complete" badge
8. **T=129s** - Auto-refresh detects no running tests, stops polling

### Scenario: Multi-tab usage

```
Tab 1                          Tab 2
─────                          ─────
User starts test        →      
                               [Auto-refresh detects running test]
                               Shows running indicator
Test running...         
                               [Auto-refresh every 3s]
                               Still shows running...
Test completes          
                               [Auto-refresh picks up completion]
                               Shows complete status
```

## Summary

The implementation provides:
- ✅ **Immediate Feedback**: Tests appear in history as soon as they start
- ✅ **Clear Status**: Visual indicators for pending, running, complete, error
- ✅ **Auto-Updates**: History refreshes automatically while tests run
- ✅ **Multi-User**: Works across tabs and sessions
- ✅ **Backward Compatible**: Existing tests work without changes
- ✅ **Crash Resilient**: Status persists even if backend crashes
