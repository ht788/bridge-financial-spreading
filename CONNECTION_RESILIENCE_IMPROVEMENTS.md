# Connection Resilience Improvements

## Overview
This document describes the improvements made to increase the resilience of the Testing Lab connection to the backend API.

## Problem
The Testing Lab was showing "Disconnected (signal timed out)" messages frequently, causing a poor user experience and potential failures during test runs.

## Solutions Implemented

### 1. Connection Monitor Improvements (`frontend/src/utils/connectionMonitor.ts`)

#### Increased Timeout
- Changed health check timeout from **5 seconds to 15 seconds**
- Uses `AbortController` instead of `AbortSignal.timeout()` for better compatibility

#### Automatic Retry with Exponential Backoff
- Implements **3 retry attempts** for each connection check
- Uses exponential backoff: 1s, 2s, 4s (capped at 5s)
- Only reports disconnection after all retries fail
- Shows "Reconnecting..." status with retry count during reconnection attempts

#### Adaptive Check Intervals
- **Connected state**: Checks every 30 seconds (reduced network traffic)
- **Disconnected state**: Checks every 5 seconds (faster recovery detection)
- Automatically adjusts based on connection status

#### Better Error Messages
- Converts technical errors to user-friendly messages
- Distinguishes between timeout, network error, and HTTP errors
- Truncates long error messages to 50 characters

### 2. Testing API Client Improvements (`frontend/src/testingApi.ts`)

#### Increased Overall Timeout
- Changed request timeout from **10 minutes to 15 minutes**
- Accommodates longer test runs without timing out

#### Smart Retry Logic
- Implements automatic retry with exponential backoff for most API calls
- **Retries 3 times** with delays: 1s, 2s, 4s
- Does NOT retry:
  - Client errors (4xx status codes) - these are user/config issues
  - Test run operations - these are expensive and may have side effects
- Only retries network/server errors that are likely transient

#### Methods with Retry Support
- `getStatus()` - Gets testing system configuration
- `getHistory()` - Retrieves test history
- `getResult()` - Gets specific test result
- `getAnswerKey()` - Retrieves company answer key
- `updateAnswerKey()` - Updates answer key
- `getPromptContent()` - Gets current prompt content

### 3. UI Improvements (`frontend/src/components/testing/TestingPage.tsx`)

#### Three-State Connection Indicator
1. **Connected** (green) - Shows latency in ms
2. **Reconnecting** (yellow) - Shows animated spinner and retry count
3. **Disconnected** (red) - Shows error message on hover

#### Manual Reconnect Button
- Appears when connection is lost
- Allows user to manually trigger reconnection attempt
- Styled with red accent to match disconnected state

## Benefits

### For Users
1. **Fewer false disconnections** - Transient network blips are automatically retried
2. **Better feedback** - Clear indication of connection status and recovery attempts
3. **Manual control** - Can trigger reconnection without refreshing the page
4. **Reduced network overhead** - Less frequent checks when connected
5. **Faster recovery** - More frequent checks when disconnected

### For Long-Running Operations
1. **Longer timeout** - 15 minutes instead of 10 minutes for test runs
2. **Automatic retry** - Most read operations automatically retry on failure
3. **Better error handling** - Clear distinction between retryable and non-retryable errors

## Configuration

### Adjustable Parameters

In `connectionMonitor.ts`:
```typescript
private maxRetries: number = 3;
private connectedCheckInterval: number = 30000; // 30 seconds
private disconnectedCheckInterval: number = 5000; // 5 seconds
```

In `testingApi.ts`:
```typescript
timeout: 900000, // 15 minutes
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000; // Base delay
```

## Testing Recommendations

1. **Test network interruptions**: Disconnect network temporarily to verify reconnection
2. **Test slow connections**: Throttle network to verify timeout handling
3. **Test backend restart**: Stop/start backend to verify recovery
4. **Test long operations**: Run multi-file test suites to verify timeout adequacy

## Future Enhancements

Potential improvements for future consideration:

1. **WebSocket fallback** - Use WebSocket for real-time connection status
2. **Offline mode** - Cache results for viewing when disconnected
3. **Progressive retry** - Increase retry delays after repeated failures
4. **Connection quality indicator** - Show connection strength (latency-based)
5. **Background sync** - Queue operations when offline, sync when reconnected
6. **Configurable timeouts** - Allow users to adjust timeouts in settings
