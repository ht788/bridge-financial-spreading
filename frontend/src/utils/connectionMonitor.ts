/**
 * Connection Monitor for Backend Health Checks
 * 
 * Monitors the connection to the backend API and reports status.
 * Handles React StrictMode double-mounting and prevents race conditions.
 */

// Use relative URL to go through Vite proxy (avoids CORS issues in development)
const getApiBaseUrl = () => {
  // If explicitly set, use it
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  // In development, use relative path to go through Vite proxy
  return '';
};

const API_BASE_URL = getApiBaseUrl();

export interface ConnectionStatus {
  isConnected: boolean;
  lastCheck: Date;
  latency: number | null;
  error: string | null;
  isRetrying?: boolean;
  retryCount?: number;
}

export class ConnectionMonitor {
  private listeners: Set<(status: ConnectionStatus) => void> = new Set();
  private intervalId: number | null = null;
  private currentStatus: ConnectionStatus = {
    isConnected: false,
    lastCheck: new Date(),
    latency: null,
    error: null,
  };
  private failureCount: number = 0;
  private maxRetries: number = 2; // Reduced from 3 for faster feedback
  private connectedCheckInterval: number = 30000; // 30 seconds when connected
  private disconnectedCheckInterval: number = 10000; // 10 seconds when disconnected (increased from 5s)
  private isRunning: boolean = false;
  private isChecking: boolean = false; // Prevent concurrent checks
  private abortController: AbortController | null = null;
  private instanceId: string = Math.random().toString(36).substring(7);

  constructor() {}

  /**
   * Start monitoring connection
   */
  start() {
    // Prevent multiple starts
    if (this.isRunning) {
      console.log(`[CONNECTION MONITOR ${this.instanceId}] Already running, skipping start`);
      return;
    }
    
    console.log(`[CONNECTION MONITOR ${this.instanceId}] Starting...`);
    this.isRunning = true;
    
    // Do initial check (don't await, but track it)
    this.performCheck();
    
    // Schedule recurring checks
    this.scheduleNextCheck();
  }

  /**
   * Stop monitoring and abort any pending requests
   */
  stop() {
    console.log(`[CONNECTION MONITOR ${this.instanceId}] Stopping...`);
    this.isRunning = false;
    
    // Clear scheduled check
    if (this.intervalId !== null) {
      clearTimeout(this.intervalId);
      this.intervalId = null;
    }
    
    // Abort any pending request
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    
    this.isChecking = false;
  }

  /**
   * Schedule the next connection check based on current status
   */
  private scheduleNextCheck() {
    if (!this.isRunning) return;
    
    if (this.intervalId !== null) {
      clearTimeout(this.intervalId);
    }
    
    const interval = this.currentStatus.isConnected 
      ? this.connectedCheckInterval 
      : this.disconnectedCheckInterval;
    
    this.intervalId = window.setTimeout(() => {
      if (this.isRunning) {
        this.performCheck();
        this.scheduleNextCheck();
      }
    }, interval);
  }

  /**
   * Perform a connection check (wrapper to prevent concurrent checks)
   */
  private async performCheck() {
    // Prevent concurrent checks
    if (this.isChecking) {
      console.log(`[CONNECTION MONITOR ${this.instanceId}] Check already in progress, skipping`);
      return;
    }
    
    this.isChecking = true;
    try {
      await this.checkConnection();
    } finally {
      this.isChecking = false;
    }
  }

  /**
   * Check connection health with retry logic
   */
  private async checkConnection() {
    if (!this.isRunning) return;
    
    let lastError: any = null;
    
    // Create a new abort controller for this check
    this.abortController = new AbortController();
    const signal = this.abortController.signal;
    
    // Try up to maxRetries times with exponential backoff
    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      // Check if we should stop
      if (!this.isRunning || signal.aborted) {
        console.log(`[CONNECTION MONITOR ${this.instanceId}] Check cancelled`);
        return;
      }
      
      try {
        // Only log first attempt or after actual failures
        if (attempt === 1) {
          console.log(`[CONNECTION MONITOR ${this.instanceId}] Checking connection...`);
        }
        
        // Update status to show we're retrying
        if (attempt > 1) {
          this.updateStatus({
            ...this.currentStatus,
            isRetrying: true,
            retryCount: attempt - 1,
          });
        }
        
        const startTime = Date.now();
        
        // Create a timeout that will abort the request
        const timeoutMs = 5000; // 5 second timeout (reduced from 15s)
        const timeoutId = setTimeout(() => {
          if (this.abortController && !signal.aborted) {
            this.abortController.abort();
          }
        }, timeoutMs);
        
        const response = await fetch(`${API_BASE_URL}/api/health`, {
          method: 'GET',
          signal: signal,
        });

        clearTimeout(timeoutId);
        const latency = Date.now() - startTime;
        
        if (response.ok) {
          console.log(`[CONNECTION MONITOR ${this.instanceId}] ✓ Connected (${latency}ms)`);
          this.failureCount = 0;
          this.updateStatus({
            isConnected: true,
            lastCheck: new Date(),
            latency,
            error: null,
            isRetrying: false,
            retryCount: 0,
          });
          return; // Success
        } else {
          lastError = new Error(`HTTP ${response.status}`);
        }
      } catch (err: any) {
        lastError = err;
        
        // If aborted by stop(), exit gracefully
        if (err.name === 'AbortError' && !this.isRunning) {
          return;
        }
        
        // If this isn't the last attempt and we're still running, wait before retrying
        if (attempt < this.maxRetries && this.isRunning) {
          const backoffMs = 1000 * attempt; // Linear backoff: 1s, 2s
          await this.sleep(backoffMs, signal);
        }
      }
    }
    
    // All retries failed
    if (!this.isRunning) return;
    
    this.failureCount++;
    const errorMessage = this.getErrorMessage(lastError);
    console.log(`[CONNECTION MONITOR ${this.instanceId}] Connection check failed: ${errorMessage}`);
    
    this.updateStatus({
      isConnected: false,
      lastCheck: new Date(),
      latency: null,
      error: errorMessage,
      isRetrying: false,
      retryCount: 0,
    });
  }

  /**
   * Sleep with abort support
   */
  private sleep(ms: number, signal: AbortSignal): Promise<void> {
    return new Promise((resolve) => {
      const timeoutId = setTimeout(resolve, ms);
      signal.addEventListener('abort', () => {
        clearTimeout(timeoutId);
        resolve();
      }, { once: true });
    });
  }

  /**
   * Convert error to user-friendly message
   */
  private getErrorMessage(err: any): string {
    if (!err) return 'Connection failed';
    
    const message = err.message || String(err);
    
    // Handle AbortController timeout/abort
    if (err.name === 'AbortError' || message.includes('abort')) {
      return 'Request timed out';
    }
    
    // Handle network errors
    if (message.includes('NetworkError') || message.includes('Failed to fetch') || message.includes('fetch')) {
      return 'Backend unavailable';
    }
    
    // Handle HTTP errors
    if (message.includes('HTTP')) {
      return message;
    }
    
    return message.substring(0, 50);
  }

  /**
   * Update status and notify listeners
   */
  private updateStatus(status: ConnectionStatus) {
    this.currentStatus = status;
    this.listeners.forEach(listener => {
      try {
        listener(status);
      } catch (e) {
        // Ignore listener errors
      }
    });
  }

  /**
   * Manually trigger a connection check
   */
  async manualCheck(): Promise<void> {
    console.log(`[CONNECTION MONITOR ${this.instanceId}] Manual check triggered`);
    // Force a new check even if one is in progress
    this.isChecking = false;
    if (this.abortController) {
      this.abortController.abort();
    }
    await this.performCheck();
  }

  /**
   * Get current status
   */
  getStatus(): ConnectionStatus {
    return this.currentStatus;
  }

  /**
   * Subscribe to status changes
   */
  subscribe(listener: (status: ConnectionStatus) => void): () => void {
    this.listeners.add(listener);
    
    // Immediately call with current status
    listener(this.currentStatus);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }
}

// Export singleton instance
export const connectionMonitor = new ConnectionMonitor();
