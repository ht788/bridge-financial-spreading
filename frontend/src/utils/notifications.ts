/**
 * Browser Notification Utilities
 * 
 * Handles requesting permission and showing notifications for completed operations
 */

export type NotificationPermissionState = 'granted' | 'denied' | 'default';

/**
 * Check if browser supports notifications
 */
export function isNotificationSupported(): boolean {
  return 'Notification' in window;
}

/**
 * Get current notification permission status
 */
export function getNotificationPermission(): NotificationPermissionState {
  if (!isNotificationSupported()) {
    return 'denied';
  }
  return Notification.permission as NotificationPermissionState;
}

/**
 * Request notification permission from user
 */
export async function requestNotificationPermission(): Promise<NotificationPermissionState> {
  if (!isNotificationSupported()) {
    console.warn('[NOTIFICATIONS] Browser does not support notifications');
    return 'denied';
  }

  if (Notification.permission === 'granted') {
    return 'granted';
  }

  if (Notification.permission === 'denied') {
    return 'denied';
  }

  try {
    const permission = await Notification.requestPermission();
    console.log('[NOTIFICATIONS] Permission:', permission);
    return permission as NotificationPermissionState;
  } catch (error) {
    console.error('[NOTIFICATIONS] Error requesting permission:', error);
    return 'denied';
  }
}

/**
 * Check if page is currently visible/focused
 */
export function isPageVisible(): boolean {
  return document.visibilityState === 'visible';
}

/**
 * Show a notification (only if page is not visible and permission granted)
 */
export function showNotification(
  title: string,
  options?: NotificationOptions & {
    autoClose?: number;
    onClick?: () => void;
  }
): Notification | null {
  if (!isNotificationSupported()) {
    console.warn('[NOTIFICATIONS] Notifications not supported');
    return null;
  }

  if (Notification.permission !== 'granted') {
    console.warn('[NOTIFICATIONS] Permission not granted');
    return null;
  }

  // Only show notification if user is on a different tab/window
  if (isPageVisible()) {
    console.log('[NOTIFICATIONS] Page is visible, skipping notification');
    return null;
  }

  try {
    const notification = new Notification(title, {
      icon: '/icon-192.png', // You can add a proper icon
      badge: '/icon-192.png',
      requireInteraction: false,
      ...options,
    });

    // Handle click to focus window
    notification.onclick = () => {
      window.focus();
      notification.close();
      if (options?.onClick) {
        options.onClick();
      }
    };

    // Auto-close after specified time (default 5 seconds)
    const autoClose = options?.autoClose ?? 5000;
    if (autoClose > 0) {
      setTimeout(() => {
        notification.close();
      }, autoClose);
    }

    return notification;
  } catch (error) {
    console.error('[NOTIFICATIONS] Error showing notification:', error);
    return null;
  }
}

/**
 * Show a test completion notification
 */
export function notifyTestComplete(
  companyName: string,
  score: number,
  grade: string,
  executionTime: number
): void {
  const minutes = Math.floor(executionTime / 60);
  const seconds = Math.round(executionTime % 60);
  const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;

  const emoji = score >= 90 ? '🎉' : score >= 70 ? '✅' : '⚠️';
  
  showNotification(
    `${emoji} Test Complete - ${companyName}`,
    {
      body: `Score: ${score.toFixed(1)}% (${grade})\nTime: ${timeStr}`,
      tag: 'test-complete',
      autoClose: 8000,
    }
  );
}

/**
 * Show a spreading completion notification
 */
export function notifySpreadComplete(
  filename: string,
  extractionRate: number,
  docType: string
): void {
  const emoji = extractionRate >= 0.9 ? '🎉' : extractionRate >= 0.7 ? '✅' : '⚠️';
  const percentage = (extractionRate * 100).toFixed(0);
  
  showNotification(
    `${emoji} Spreading Complete`,
    {
      body: `${filename}\n${docType === 'auto' ? 'Auto-detected statements' : docType === 'income' ? 'Income Statement' : 'Balance Sheet'}\nExtraction: ${percentage}%`,
      tag: 'spread-complete',
      autoClose: 8000,
    }
  );
}

/**
 * Show a batch spreading completion notification
 */
export function notifyBatchComplete(
  totalFiles: number,
  successCount: number,
  executionTime: number
): void {
  const minutes = Math.floor(executionTime / 60);
  const seconds = Math.round(executionTime % 60);
  const timeStr = minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;

  const emoji = successCount === totalFiles ? '🎉' : successCount > 0 ? '✅' : '❌';
  
  showNotification(
    `${emoji} Batch Processing Complete`,
    {
      body: `${successCount}/${totalFiles} files processed successfully\nTime: ${timeStr}`,
      tag: 'batch-complete',
      autoClose: 8000,
    }
  );
}

/**
 * Show an error notification
 */
export function notifyError(
  title: string,
  message: string
): void {
  showNotification(
    `❌ ${title}`,
    {
      body: message,
      tag: 'error',
      autoClose: 10000,
    }
  );
}
