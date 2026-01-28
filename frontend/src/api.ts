/**
 * API client for the Bridge Financial Spreader backend
 * 
 * Note: WebSocket management has been moved to utils/connectionManager.ts
 * for unified connection handling with robust reconnection logic.
 */

import axios from 'axios';
import { 
  SpreadResponse, 
  SpreadRequest, 
  BatchSpreadResponse, 
  FileUploadItem,
  LogEntry,
} from './types';

export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

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
    
    if (request.model_override !== undefined) {
      formData.append('model_override', request.model_override);
    }
    
    if (request.extended_thinking !== undefined) {
      formData.append('extended_thinking', String(request.extended_thinking));
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
   * 
   * Files are processed in parallel by default for improved performance.
   * When doc_type='auto' is used, each file also extracts both IS and BS in parallel.
   */
  async spreadBatch(files: FileUploadItem[], options?: {
    period?: string;
    max_pages?: number;
    dpi?: number;
    model_override?: string;
    extended_thinking?: boolean;
    parallel?: boolean;  // Default: true - process files in parallel
    max_concurrent?: number;  // Default: 4 - max concurrent file extractions
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
    if (options?.model_override !== undefined) {
      formData.append('model_override', options.model_override);
    }
    if (options?.extended_thinking !== undefined) {
      formData.append('extended_thinking', String(options.extended_thinking));
    }
    // Parallel processing options (both default to optimal values on backend)
    if (options?.parallel !== undefined) {
      formData.append('parallel', String(options.parallel));
    }
    if (options?.max_concurrent !== undefined) {
      formData.append('max_concurrent', String(options.max_concurrent));
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

  /**
   * Force restart the backend server
   */
  async restartBackend(): Promise<{ success: boolean; message: string }> {
    // Call the startup service on port 8001
    const response = await fetch('http://localhost:8001/restart', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    return await response.json();
  },
};
