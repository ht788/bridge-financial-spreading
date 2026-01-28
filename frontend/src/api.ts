/**
 * API client for the Bridge Financial Spreader backend
 */

import axios from 'axios';
import { 
  SpreadResponse, 
  SpreadRequest, 
  BatchSpreadResponse, 
  FileUploadItem,
  LogEntry,
  ProcessingStep,
  WebSocketMessage
} from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';
// WebSocket URL - use Vite proxy in development, direct connection in production
// In development, Vite proxies /ws to ws://localhost:8000
const getWsBaseUrl = () => {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  // In development, use relative path to go through Vite proxy
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return '';
  }
  // In production, use same host
  return (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host;
};
const WS_BASE_URL = getWsBaseUrl();

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

// =============================================================================
// WEBSOCKET MANAGER
// =============================================================================

type MessageHandler = (message: WebSocketMessage) => void;
type ConnectionHandler = (connected: boolean) => void;

class WebSocketManager {
  private ws: WebSocket | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: NodeJS.Timeout | null = null;

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return;
    }

    const wsUrl = `${WS_BASE_URL}/ws/progress`;
    console.log('[WebSocket] Connecting to:', wsUrl);
    
    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected');
        this.reconnectAttempts = 0;
        this.notifyConnectionHandlers(true);
        this.startPingInterval();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage;
          this.notifyMessageHandlers(message);
        } catch (e) {
          // Handle non-JSON messages (like "pong")
          if (event.data !== 'pong') {
            console.log('[WebSocket] Non-JSON message:', event.data);
          }
        }
      };

      this.ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        this.notifyConnectionHandlers(false);
        this.stopPingInterval();
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };
    } catch (error) {
      console.error('[WebSocket] Failed to connect:', error);
      this.attemptReconnect();
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      setTimeout(() => this.connect(), delay);
    } else {
      console.log('[WebSocket] Max reconnection attempts reached');
    }
  }

  private startPingInterval() {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send('ping');
      }
    }, 30000);
  }

  private stopPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  disconnect() {
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  onMessage(handler: MessageHandler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onConnectionChange(handler: ConnectionHandler) {
    this.connectionHandlers.add(handler);
    return () => this.connectionHandlers.delete(handler);
  }

  private notifyMessageHandlers(message: WebSocketMessage) {
    this.messageHandlers.forEach(handler => handler(message));
  }

  private notifyConnectionHandlers(connected: boolean) {
    this.connectionHandlers.forEach(handler => handler(connected));
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

export const wsManager = new WebSocketManager();

// =============================================================================
// API FUNCTIONS
// =============================================================================

export const api = {
  /**
   * Upload and spread a financial statement PDF
   */
  async spreadFinancialStatement(request: SpreadRequest): Promise<SpreadResponse> {
    const formData = new FormData();
    formData.append('file', request.file);
    formData.append('doc_type', request.doc_type);
    if (request.period !== undefined) {
      formData.append('period', request.period);
    }
    
    if (request.max_pages !== undefined) {
      formData.append('max_pages', String(request.max_pages));
    }
    
    if (request.dpi !== undefined) {
      formData.append('dpi', String(request.dpi));
    }

    const response = await apiClient.post<SpreadResponse>('/spread', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Upload and spread multiple financial statement PDFs
   */
  async spreadBatch(files: FileUploadItem[], options?: {
    period?: string;
    max_pages?: number;
    dpi?: number;
  }): Promise<BatchSpreadResponse> {
    const formData = new FormData();
    
    // Append each file
    files.forEach(item => {
      formData.append('files', item.file);
    });
    
    // Append doc_types as JSON array
    const docTypes = files.map(f => f.docType);
    formData.append('doc_types', JSON.stringify(docTypes));
    
    // Append options
    if (options?.period !== undefined) {
      formData.append('period', options.period);
    }
    if (options?.max_pages !== undefined) {
      formData.append('max_pages', String(options.max_pages));
    }
    if (options?.dpi !== undefined) {
      formData.append('dpi', String(options.dpi));
    }

    const response = await apiClient.post<BatchSpreadResponse>('/spread/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });

    return response.data;
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; version: string; timestamp: string }> {
    const response = await apiClient.get('/health');
    return response.data;
  },

  /**
   * Get recent logs
   */
  async getLogs(limit: number = 100): Promise<{ logs: LogEntry[] }> {
    const response = await apiClient.get(`/logs?limit=${limit}`);
    return response.data;
  },

  /**
   * Get PDF URL for viewing
   */
  getPdfUrl(filename: string): string {
    return `${API_BASE_URL}/files/${filename}`;
  },

  /**
   * Start the backend server
   */
  async startBackend(): Promise<{ success: boolean; message: string }> {
    // Call the startup service on port 8001
    const response = await fetch('http://localhost:8001/start', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return await response.json();
  },
};
