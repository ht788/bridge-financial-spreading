# In-Progress Test Tracking Feature

## Overview

The testing system now tracks and displays in-progress tests in the test history, providing real-time visibility into running tests.

## Implementation Summary

### Database Schema Changes

- **Added `status` column** to the `test_runs` table with values:
  - `pending`: Test has been created but not started
  - `running`: Test is currently executing
  - `complete`: Test finished successfully
  - `error`: Test failed with error

- **Migration Support**: Existing records automatically default to `complete` status
- **UPDATE Support**: Changed from `INSERT` to `INSERT OR REPLACE` to allow updating test records

### Backend Changes

#### `test_models.py`
- Added `TestRunStatus` enum with status values
- Updated `TestRunResult` to include `status` field (defaults to `pending`)
- Updated `TestRunSummary` to include `status` field
- Made `overall_score` and `overall_grade` optional for in-progress tests

#### `test_runner.py`
- **Immediate Persistence**: Test record is saved to database as soon as `run_test()` starts with `RUNNING` status
- **Progress Tracking**: Test status is updated to `COMPLETE` or `ERROR` when finished
- **Database Updates**: Uses `INSERT OR REPLACE` to update existing records

### Frontend Changes

#### `testingTypes.ts`
- Added `TestRunStatus` type
- Updated `TestRunResult` and `TestRunSummary` interfaces to include `status`
- Added helper functions:
  - `getStatusColor()`: Returns Tailwind classes for status badge styling
  - `getStatusLabel()`: Returns human-readable status labels

#### `TestHistoryTable.tsx`
- **New Status Column**: Displays test execution status with appropriate styling
- **Running Test Indicators**:
  - Animated spinner icon for running tests
  - "In progress..." placeholder for grade/score
  - "Running..." text for duration
  - Disabled "View" button with "In progress" text
- **Visual Feedback**: Blue badge with spinner for running tests

#### `TestingPage.tsx`
- **Auto-Refresh**: Automatically refreshes history every 3 seconds when running tests are detected
- **Smart Polling**: Stops auto-refresh when no tests are running
- **Cleanup**: Properly clears intervals on component unmount

## User Experience

### Before Running a Test
1. User configures and starts a test
2. Test appears in history **immediately** with "Running" status
3. Grade, score, and duration show as "In progress..." or "—"

### During Test Execution
1. Status badge shows blue "Running" with animated spinner
2. History auto-refreshes every 3 seconds
3. User can see the test in the history table but cannot view details yet

### After Test Completion
1. Test status updates to "Complete" or "Error"
2. Grade and score become visible
3. "View" button becomes active
4. Auto-refresh stops when no tests are running

## Benefits

1. **Visibility**: Users can see tests running in real-time
2. **Multi-Tab Support**: Multiple users/tabs can see when tests are in progress
3. **Crash Recovery**: If backend crashes during a test, the "Running" status persists
4. **Better UX**: No more wondering if a test started or is still running

## Technical Details

### Database Migration
The implementation includes automatic migration that:
- Checks if `status` column exists
- Adds it if missing with default value `complete`
- Existing test records remain valid

### Error Handling
- If saving initial state fails, test continues but may not appear in history immediately
- Final state is always saved regardless of initial save success
- Errors during test execution result in `ERROR` status

### Performance
- Auto-refresh uses efficient 3-second intervals
- Polling only occurs when running tests are detected
- Database queries remain fast with indexed `timestamp` ordering

## Future Enhancements

Potential improvements:
1. WebSocket-based real-time updates instead of polling
2. Progress percentage in the history table
3. Ability to cancel running tests
4. Show which file is currently being processed
5. Estimated time remaining based on average file processing time
