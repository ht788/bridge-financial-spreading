# Browser Notification Feature

## Overview

Added browser push notifications that alert users when spreading operations or tests complete, particularly useful when the user has switched to another tab or window.

## Features

### 1. Notification Utility (`frontend/src/utils/notifications.ts`)

A comprehensive notification system with:

- **Permission Management**: Request and check notification permissions
- **Visibility Detection**: Only show notifications when the page is not visible/active
- **Auto-close**: Notifications auto-close after a configurable timeout (default 5 seconds)
- **Click Handler**: Clicking notification brings the browser window into focus

### 2. Notification Types

#### Test Completion Notification
```typescript
notifyTestComplete(companyName, score, grade, executionTime)
```
Shows:
- Company name
- Test score and grade
- Execution time
- Emoji indicator (🎉 for >=90%, ✅ for >=70%, ⚠️ for <70%)

#### Spreading Completion Notification
```typescript
notifySpreadComplete(filename, extractionRate, docType)
```
Shows:
- Filename
- Document type (Income Statement, Balance Sheet, or Auto-detected)
- Extraction rate percentage
- Emoji indicator based on extraction quality

#### Batch Processing Notification
```typescript
notifyBatchComplete(totalFiles, successCount, executionTime)
```
Shows:
- Success/total files count
- Total execution time
- Success indicator emoji

#### Error Notification
```typescript
notifyError(title, message)
```
Shows:
- Error title
- Error message
- Red X emoji (❌)

### 3. Header Integration

Added a notification bell button in the Header component:

- **Notification Off**: Bell icon, click to enable
- **Notification On**: Green bell icon, shows "Notifications On"
- **Blocked**: Red bell-off icon, prompts user to enable in browser settings
- **Test Notification**: Shows a test notification when first enabled

The button:
- Only appears in browsers that support notifications
- Shows current permission state with appropriate styling
- Includes helpful tooltips

### 4. Integration Points

**App.tsx (Regular Spreading)**:
- Single file completion
- Batch processing completion
- Error notifications

**TestingPage.tsx (Testing Lab)**:
- Test run completion with score and grade
- Test run errors

## User Flow

1. **First Time**: User sees "Enable Notifications" button in header
2. **Click Button**: Browser shows permission prompt
3. **Grant Permission**: Test notification appears confirming setup
4. **During Processing**: User can switch tabs/windows
5. **On Completion**: Browser notification appears (only if tab is not active)
6. **Click Notification**: Returns user to the app

## Technical Details

### Notification Conditions

Notifications only appear when:
1. Permission is granted
2. Browser supports notifications
3. Page is not currently visible (`document.visibilityState !== 'visible'`)

This prevents annoying duplicate notifications when the user is already looking at the page.

### Browser Compatibility

Works in:
- Chrome/Edge (Chromium)
- Firefox
- Safari (macOS 10.14+)
- Opera

### Icons

The notification system references `/icon-192.png` for notification icons. You can add this to the public folder for branded notifications.

## Testing

To test notifications:

1. Start the application
2. Click "Enable Notifications" in the header
3. Grant permission in the browser prompt
4. Start a spreading operation or test
5. Switch to another tab
6. Wait for completion - notification should appear

## Future Enhancements

Possible improvements:
- Sound alerts (optional)
- Notification history/log
- Custom notification settings (enable/disable per operation type)
- Desktop notification persistence settings
- Different notification sounds for success vs. error
