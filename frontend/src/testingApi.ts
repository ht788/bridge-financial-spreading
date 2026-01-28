/**
 * API client for the Testing System
 */

import axios, { AxiosError, AxiosInstance } from 'axios';
import {
  TestingStatusResponse,
  TestRunConfig,
  TestRunResult,
  TestHistoryResponse,
  CompanyAnswerKey
} from './testingTypes';

// Use relative URL to go through Vite proxy (avoids CORS issues in development)
const getApiBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  // In development, use relative path to go through Vite proxy
  return '';
};

const API_BASE_URL = getApiBaseUrl();

// Create two axios instances: one for quick operations, one for long-running tests
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000, // 15 second timeout for normal operations
});

const testRunClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 900000, // 15 minute timeout for long test runs
});

// Retry configuration
const MAX_RETRIES = 2; // Reduced from 3 for faster feedback
const RETRY_DELAY_MS = 500; // Reduced from 1000 for faster retries

/**
 * Retry wrapper with exponential backoff
 */
async function withRetry<T>(
  fn: () => Promise<T>,
  retries: number = MAX_RETRIES,
  operationName: string = 'operation'
): Promise<T> {
  let lastError: any;
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;
      
      // Don't retry on 4xx errors (client errors) or successful responses
      if (error.response && error.response.status >= 400 && error.response.status < 500) {
        console.error(`[TESTING API] ${operationName} failed with client error ${error.response.status}, not retrying`);
        throw error;
      }
      
      // Don't retry on last attempt
      if (attempt === retries) {
        console.error(`[TESTING API] ${operationName} failed after ${retries} attempts`);
        throw error;
      }
      
      // Calculate backoff delay
      const delay = RETRY_DELAY_MS * Math.pow(2, attempt - 1); // Exponential backoff
      console.warn(
        `[TESTING API] ${operationName} failed (attempt ${attempt}/${retries}): ${error.message}. ` +
        `Retrying in ${delay}ms...`
      );
      
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError;
}

// Setup interceptors for a client
const setupInterceptors = (client: AxiosInstance, clientName: string) => {
  client.interceptors.request.use(
    (config) => {
      console.log(`[${clientName}] → ${config.method?.toUpperCase()} ${config.url}`);
      return config;
    },
    (error) => {
      console.error(`[${clientName}] Request error:`, error.message);
      return Promise.reject(error);
    }
  );

  client.interceptors.response.use(
    (response) => {
      console.log(`[${clientName}] ← ${response.status} ${response.config.url}`);
      return response;
    },
    (error: AxiosError) => {
      const status = error.response?.status;
      const code = error.code;
      
      // Only log meaningful errors
      if (code === 'ECONNABORTED') {
        console.error(`[${clientName}] ❌ Request timeout`);
      } else if (code === 'ERR_NETWORK') {
        console.error(`[${clientName}] ❌ Network error - backend unavailable`);
      } else if (status) {
        console.error(`[${clientName}] ❌ HTTP ${status}: ${error.message}`);
      } else {
        console.error(`[${clientName}] ❌ ${error.message}`);
      }
      
      return Promise.reject(error);
    }
  );
};

// Setup interceptors for both clients
setupInterceptors(apiClient, 'TESTING API');
setupInterceptors(testRunClient, 'TEST RUN');

export const testingApi = {
  /**
   * Get testing system status (companies, models, current prompt)
   */
  async getStatus(): Promise<TestingStatusResponse> {
    console.log('[TESTING API] Getting status...');
    return withRetry(async () => {
      const response = await apiClient.get<TestingStatusResponse>('/api/testing/status');
      console.log('[TESTING API] Status retrieved:', {
        companies: response.data.available_companies.length,
        models: response.data.available_models.length
      });
      return response.data;
    }, MAX_RETRIES, 'getStatus');
  },

  /**
   * Run a test with the given configuration
   */
  async runTest(config: TestRunConfig): Promise<TestRunResult> {
    console.log('[TESTING API] Starting test run...', {
      companyId: config.company_id,
      model: config.model_name,
      hasPromptOverride: !!config.prompt_override
    });
    
    const startTime = Date.now();
    
    // Don't retry test runs - they're expensive and may have side effects
    // Use the long-timeout client for test runs
    const response = await testRunClient.post<TestRunResult>('/api/testing/run', config);
    const duration = Date.now() - startTime;
    
    console.log('[TESTING API] Test run completed:', {
      testId: response.data.id,
      score: response.data.overall_score,
      grade: response.data.overall_grade,
      duration: `${(duration / 1000).toFixed(1)}s`
    });
    
    return response.data;
  },

  /**
   * Get test history
   */
  async getHistory(limit: number = 50, companyId?: string): Promise<TestHistoryResponse> {
    console.log('[TESTING API] Getting history...', { limit, companyId });
    return withRetry(async () => {
      const params: Record<string, string | number> = { limit };
      if (companyId) {
        params.company_id = companyId;
      }
      const response = await apiClient.get<TestHistoryResponse>('/api/testing/history', { params });
      console.log('[TESTING API] History retrieved:', {
        runs: response.data.runs.length,
        total: response.data.total_count
      });
      return response.data;
    }, MAX_RETRIES, 'getHistory');
  },

  /**
   * Get a specific test result by ID
   */
  async getResult(testId: string): Promise<TestRunResult> {
    console.log('[TESTING API] Getting test result:', testId);
    return withRetry(async () => {
      const response = await apiClient.get<TestRunResult>(`/api/testing/result/${testId}`);
      console.log('[TESTING API] Test result retrieved:', {
        testId: response.data.id,
        score: response.data.overall_score,
        files: response.data.total_files
      });
      return response.data;
    }, MAX_RETRIES, 'getResult');
  },

  /**
   * Get answer key for a company
   */
  async getAnswerKey(companyId: string): Promise<CompanyAnswerKey> {
    return withRetry(async () => {
      const response = await apiClient.get<CompanyAnswerKey>(`/api/testing/answer-key/${companyId}`);
      return response.data;
    }, MAX_RETRIES, 'getAnswerKey');
  },

  /**
   * Update answer key for a company
   */
  async updateAnswerKey(answerKey: CompanyAnswerKey): Promise<{ success: boolean; message: string }> {
    return withRetry(async () => {
      const response = await apiClient.put<{ success: boolean; message: string }>('/api/testing/answer-key', answerKey);
      return response.data;
    }, MAX_RETRIES, 'updateAnswerKey');
  },

  /**
   * Get current prompt content
   */
  async getPromptContent(docType: string = 'income'): Promise<{ doc_type: string; content: string | null }> {
    return withRetry(async () => {
      const response = await apiClient.get<{ doc_type: string; content: string | null }>(`/api/testing/prompt/${docType}`);
      return response.data;
    }, MAX_RETRIES, 'getPromptContent');
  }
};
