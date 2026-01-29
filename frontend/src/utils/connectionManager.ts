/**
 * Unified Connection Manager
 * 
 * Manages both HTTP health checks and WebSocket connections with robust
 * reconnection logic. This replaces the separate connectionMonitor and
 * WebSocketManager with a unified approach.
 * 
 * Key improvements:
 * - No hard limit on reconnection attempts (uses progressive backoff instead)
 * - Coordinates HTTP health checks with WebSocket reconnection
 * - Manual reconnect that actually works
 * - Connection state reflects both HTTP and WS status
 */

export type ConnectionState = 
  | 'connected'      // Both HTTP and WS are working
  | 'degraded'       // HTTP works but WS is down (limited functionality)
  | 'reconnecting'   // Actively trying to reconnect
  | 'disconnected';  // Backend is completely unavailable

export interface ConnectionStatus {
  state: ConnectionState;
  httpHealthy: boolean;
  wsConnected: boolean;
  lastHealthCheck: Date | null;
  lastSuccessfulConnection: Date | null;
  latencyMs: number | null;
  error: string | null;
  reconnectAttempt: number;
  nextReconnectMs: number | null;
}

export type WebSocketMessage = {
  type: string;
  job_id?: string;
  timestamp?: string;
  payload?: unknown;
};

type StatusListener = (status: ConnectionStatus) => void;
type MessageListener = (message: WebSocketMessage) => void;

// Calculate backoff with jitter - caps at 60 seconds
function calculateBackoff(attempt: number): number {
  // Base backoff: 1s, 2s, 4s, 8s, 16s, 32s, then cap at 60s
  const baseDelay = Math.min(1000 * Math.pow(2, attempt), 60000);
  // Add jitter: +/- 20%
  const jitter = baseDelay * 0.2 * (Math.random() * 2 - 1);
  return Math.round(baseDelay + jitter);
}

class ConnectionManager {
  private static instance: ConnectionManager | null = null;
  
  // Connection state
  private ws: WebSocket | null = null;
  private status: ConnectionStatus = {
    state: 'disconnected',
    httpHealthy: false,
    wsConnected: false,
    lastHealthCheck: null,
    lastSuccessfulConnection: null,
    latencyMs: null,
    error: null,
    reconnectAttempt: 0,
    nextReconnectMs: null,
  };
  
  // Listeners
  private statusListeners: Set<StatusListener> = new Set();
  private messageListeners: Set<MessageListener> = new Set();
  
  // Timers and controllers
  private healthCheckTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private wsReconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private abortController: AbortController | null = null;
  private healthCheckInFlight: Promise<boolean> | null = null;
  
  // Configuration
  private readonly healthCheckInterval = 30000; // 30s when connected
  private readonly disconnectedCheckInterval = 5000; // 5s when disconnected
  private readonly wsConnectTimeout = 10000; // 10s to establish WS connection
  private readonly httpTimeout = 15000; // 15s for health checks
  
  // State
  private isStarted = false;
  private isReconnecting = false;
  private consecutiveFailures = 0;
  private isPaused = false; // Pauses health checks during active processing
  
  private constructor() {}
  
  static getInstance(): ConnectionManager {
    if (!ConnectionManager.instance) {
      ConnectionManager.instance = new ConnectionManager();
    }
    return ConnectionManager.instance;
  }
  
  /**
   * Start the connection manager - initiates both HTTP health checks and WebSocket
   */
  start(): void {
    if (this.isStarted) {
      console.log('[ConnectionManager] Already started');
      return;
    }
    
    console.log('[ConnectionManager] Starting...');
    this.isStarted = true;
    
    // Immediately try to connect
    this.attemptConnection();
  }
  
  /**
   * Stop the connection manager and clean up all resources
   */
  stop(): void {
    console.log('[ConnectionManager] Stopping...');
    this.isStarted = false;
    
    // Clear all timers
    if (this.healthCheckTimer) {
      clearTimeout(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.wsReconnectTimer) {
      clearTimeout(this.wsReconnectTimer);
      this.wsReconnectTimer = null;
    }
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    
    // Abort any pending requests
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    
    // Close WebSocket
    this.closeWebSocket();
    
    this.isReconnecting = false;
  }
  
  /**
   * Force a manual reconnection attempt - this is what the "Reconnect" button should call
   */
  async reconnect(): Promise<void> {
    console.log('[ConnectionManager] Manual reconnect requested');
    
    // Reset state for fresh attempt
    this.consecutiveFailures = 0;
    this.isReconnecting = false;
    
    // Clear any pending reconnect timers
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.wsReconnectTimer) {
      clearTimeout(this.wsReconnectTimer);
      this.wsReconnectTimer = null;
    }
    
    // Close existing WebSocket to start fresh
    this.closeWebSocket();
    
    // Update status to show we're reconnecting
    this.updateStatus({
      state: 'reconnecting',
      error: null,
      reconnectAttempt: 0,
    });
    
    // Attempt connection
    await this.attemptConnection();
  }
  
  /**
   * Subscribe to connection status changes
   */
  onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    // Immediately notify with current status
    listener(this.status);
    return () => this.statusListeners.delete(listener);
  }
  
  /**
   * Subscribe to WebSocket messages
   */
  onMessage(listener: MessageListener): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }
  
  /**
   * Get current connection status
   */
  getStatus(): ConnectionStatus {
    return { ...this.status };
  }
  
  /**
   * Check if fully connected (both HTTP and WS)
   */
  isConnected(): boolean {
    return this.status.state === 'connected';
  }
  
  /**
   * Pause health checks - useful during long-running operations like file processing
   * This prevents misleading "Backend unavailable" messages when the backend is busy
   */
  pauseHealthChecks(): void {
    console.log('[ConnectionManager] Health checks paused (processing in progress)');
    this.isPaused = true;
    
    // Clear any pending health check timer
    if (this.healthCheckTimer) {
      clearTimeout(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }
    
    // Abort any in-progress health check request
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
  }
  
  /**
   * Resume health checks after processing completes
   */
  resumeHealthChecks(): void {
    console.log('[ConnectionManager] Health checks resumed');
    this.isPaused = false;
    
    // Immediately check health and schedule next check
    if (this.isStarted) {
      this.scheduleHealthCheck();
    }
  }
  
  /**
   * Check if health checks are currently paused
   */
  isHealthCheckPaused(): boolean {
    return this.isPaused;
  }
  
  // ==========================================================================
  // PRIVATE METHODS
  // ==========================================================================
  
  private async attemptConnection(): Promise<void> {
    if (!this.isStarted) return;
    if (this.isReconnecting) {
      console.log('[ConnectionManager] Already reconnecting, skipping');
      return;
    }
    
    this.isReconnecting = true;
    
    try {
      // Step 1: Check HTTP health first
      const httpOk = await this.checkHttpHealth();
      
      if (!httpOk) {
        // Backend is down - schedule retry
        this.consecutiveFailures++;
        this.scheduleReconnect();
        return;
      }
      
      // Step 2: HTTP is up, now connect WebSocket
      if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
        await this.connectWebSocket();
      }
      
      // If we get here and WS connected, we're fully connected
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.onFullyConnected();
      }
      
    } catch (error) {
      console.error('[ConnectionManager] Connection attempt failed:', error);
      this.consecutiveFailures++;
      this.scheduleReconnect();
    } finally {
      this.isReconnecting = false;
    }
  }
  
  private async checkHttpHealth(): Promise<boolean> {
    if (this.healthCheckInFlight) {
      return this.healthCheckInFlight;
    }

    console.log('[ConnectionManager] Checking HTTP health...');

    const controller = new AbortController();
    this.abortController = controller;
    const startTime = Date.now();

    this.healthCheckInFlight = (async () => {
      let timeoutId: ReturnType<typeof setTimeout> | null = null;
      try {
        timeoutId = setTimeout(() => {
          controller.abort();
        }, this.httpTimeout);

        const response = await fetch(`${this.getApiBaseUrl()}/health`, {
          method: 'GET',
          signal: controller.signal,
        });

        const latency = Date.now() - startTime;

        if (response.ok) {
          console.log(`[ConnectionManager] HTTP healthy (${latency}ms)`);
          this.updateStatus({
            httpHealthy: true,
            lastHealthCheck: new Date(),
            latencyMs: latency,
            error: null,
          });
          return true;
        }

        throw new Error(`HTTP ${response.status}`);
      } catch (error: unknown) {
        const errorMessage = this.getErrorMessage(error);
        console.log(`[ConnectionManager] HTTP health check failed: ${errorMessage}`);

        this.updateStatus({
          httpHealthy: false,
          lastHealthCheck: new Date(),
          latencyMs: null,
          error: errorMessage,
          state: 'disconnected',
        });

        return false;
      } finally {
        if (timeoutId) {
          clearTimeout(timeoutId);
        }
        if (this.abortController === controller) {
          this.abortController = null;
        }
        this.healthCheckInFlight = null;
      }
    })();

    return this.healthCheckInFlight;
  }
  
  private connectWebSocket(): Promise<void> {
    return new Promise((resolve, reject) => {
      console.log('[ConnectionManager] Connecting WebSocket...');
      
      // Close any existing connection
      this.closeWebSocket();
      
      const wsUrl = this.getWebSocketUrl();
      
      try {
        this.ws = new WebSocket(wsUrl);
        
        // Set up connection timeout
        const connectTimeout = setTimeout(() => {
          if (this.ws?.readyState !== WebSocket.OPEN) {
            console.log('[ConnectionManager] WebSocket connection timeout');
            this.closeWebSocket();
            reject(new Error('WebSocket connection timeout'));
          }
        }, this.wsConnectTimeout);
        
        this.ws.onopen = () => {
          clearTimeout(connectTimeout);
          console.log('[ConnectionManager] WebSocket connected');
          
          this.updateStatus({
            wsConnected: true,
          });
          
          // Start ping/pong to keep connection alive
          this.startPingInterval();
          
          resolve();
        };
        
        this.ws.onclose = (event) => {
          clearTimeout(connectTimeout);
          console.log(`[ConnectionManager] WebSocket closed: ${event.code} ${event.reason}`);
          
          this.stopPingInterval();
          this.updateStatus({
            wsConnected: false,
          });
          
          // If we're still running, schedule WS reconnect
          if (this.isStarted && !this.isReconnecting) {
            this.scheduleWsReconnect();
          }
        };
        
        this.ws.onerror = (error) => {
          clearTimeout(connectTimeout);
          console.error('[ConnectionManager] WebSocket error:', error);
          // Don't reject here - let onclose handle it
        };
        
        this.ws.onmessage = (event) => {
          this.handleWebSocketMessage(event);
        };
        
      } catch (error) {
        console.error('[ConnectionManager] Failed to create WebSocket:', error);
        reject(error);
      }
    });
  }
  
  private closeWebSocket(): void {
    if (this.ws) {
      this.ws.onclose = null; // Prevent reconnect trigger
      this.ws.onerror = null;
      this.ws.onmessage = null;
      this.ws.onopen = null;
      
      if (this.ws.readyState === WebSocket.OPEN || 
          this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close(1000, 'Client closing');
      }
      
      this.ws = null;
    }
    this.stopPingInterval();
  }
  
  private handleWebSocketMessage(event: MessageEvent): void {
    try {
      // Handle pong messages
      if (event.data === 'pong') {
        return;
      }
      
      const message = JSON.parse(event.data) as WebSocketMessage;
      this.messageListeners.forEach(listener => {
        try {
          listener(message);
        } catch (e) {
          console.error('[ConnectionManager] Message listener error:', e);
        }
      });
    } catch {
      console.log('[ConnectionManager] Non-JSON message:', event.data);
    }
  }
  
  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        try {
          this.ws.send('ping');
        } catch (error) {
          console.error('[ConnectionManager] Ping failed:', error);
        }
      }
    }, 25000); // Ping every 25 seconds
  }
  
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
  
  private onFullyConnected(): void {
    console.log('[ConnectionManager] Fully connected (HTTP + WS)');
    
    // Reset failure counter on success
    this.consecutiveFailures = 0;
    
    this.updateStatus({
      state: 'connected',
      httpHealthy: true,
      wsConnected: true,
      lastSuccessfulConnection: new Date(),
      error: null,
      reconnectAttempt: 0,
      nextReconnectMs: null,
    });
    
    // Schedule next health check
    this.scheduleHealthCheck();
  }
  
  private scheduleHealthCheck(): void {
    if (!this.isStarted) return;
    
    // Don't schedule health checks if paused (during active processing)
    if (this.isPaused) {
      console.log('[ConnectionManager] Health check skipped (paused for processing)');
      return;
    }
    
    if (this.healthCheckTimer) {
      clearTimeout(this.healthCheckTimer);
    }
    
    const interval = this.status.state === 'connected' 
      ? this.healthCheckInterval 
      : this.disconnectedCheckInterval;
    
    this.healthCheckTimer = setTimeout(async () => {
      // Double-check pause state before executing
      if (this.isPaused) {
        console.log('[ConnectionManager] Health check skipped (paused for processing)');
        return;
      }
      
      const httpOk = await this.checkHttpHealth();
      
      // Update state based on health check
      if (httpOk && this.ws?.readyState === WebSocket.OPEN) {
        this.updateStatus({ state: 'connected' });
      } else if (httpOk) {
        this.updateStatus({ state: 'degraded' });
      } else {
        this.updateStatus({ state: 'disconnected' });
        // Trigger reconnection
        this.scheduleReconnect();
        return;
      }
      
      // Schedule next check
      this.scheduleHealthCheck();
    }, interval);
  }
  
  private scheduleReconnect(): void {
    if (!this.isStarted) return;
    
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    
    const backoffMs = calculateBackoff(this.consecutiveFailures);
    console.log(`[ConnectionManager] Scheduling reconnect in ${backoffMs}ms (attempt ${this.consecutiveFailures + 1})`);
    
    this.updateStatus({
      state: 'reconnecting',
      reconnectAttempt: this.consecutiveFailures + 1,
      nextReconnectMs: backoffMs,
    });
    
    this.reconnectTimer = setTimeout(() => {
      this.isReconnecting = false;
      this.attemptConnection();
    }, backoffMs);
  }
  
  private scheduleWsReconnect(): void {
    // WebSocket dropped but HTTP might still be up
    // Try to reconnect WS specifically
    if (!this.isStarted) return;
    
    if (this.wsReconnectTimer) {
      clearTimeout(this.wsReconnectTimer);
    }
    
    // Quick retry for WS since HTTP is probably still up
    const retryMs = calculateBackoff(Math.min(this.consecutiveFailures, 3));
    console.log(`[ConnectionManager] WebSocket lost, reconnecting in ${retryMs}ms`);
    
    this.updateStatus({
      state: 'degraded',
      wsConnected: false,
    });
    
    this.wsReconnectTimer = setTimeout(async () => {
      if (!this.isStarted) return;
      
      try {
        await this.connectWebSocket();
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.onFullyConnected();
        }
      } catch {
        this.consecutiveFailures++;
        this.scheduleWsReconnect();
      }
    }, retryMs);
  }
  
  private updateStatus(partial: Partial<ConnectionStatus>): void {
    this.status = { ...this.status, ...partial };
    
    this.statusListeners.forEach(listener => {
      try {
        listener(this.status);
      } catch (e) {
        console.error('[ConnectionManager] Status listener error:', e);
      }
    });
  }
  
  private getWebSocketUrl(): string {
    const apiBaseUrl = this.getApiBaseUrl();

    // If API base URL is absolute, derive WS host from it
    if (apiBaseUrl.startsWith('http://') || apiBaseUrl.startsWith('https://')) {
      const url = new URL(apiBaseUrl);
      const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProtocol}//${url.host}/ws/progress`;
    }

    // Relative API base: use same host (Vite proxy or same-origin)
    return `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/progress`;
  }

  private getApiBaseUrl(): string {
    const configured = import.meta.env.VITE_API_URL;
    if (configured) {
      return configured.replace(/\/$/, '');
    }
    return '/api';
  }
  
  private getErrorMessage(error: unknown): string {
    if (!error) return 'Connection failed';
    
    if (error instanceof Error) {
      const message = error.message;
      
      if (error.name === 'AbortError' || message.includes('abort')) {
        return 'Request timed out';
      }
      
      if (message.includes('NetworkError') || message.includes('Failed to fetch') || message.includes('fetch')) {
        return 'Backend unavailable';
      }
      
      if (message.includes('HTTP')) {
        return message;
      }
      
      return message.length > 50 ? message.substring(0, 50) + '...' : message;
    }
    
    return String(error).substring(0, 50);
  }
}

// Export singleton instance
export const connectionManager = ConnectionManager.getInstance();

// Also export the class for testing
export { ConnectionManager };
