/**
 * API client for the Bridge Financial Spreader Testing System
 */

import axios from 'axios';
import {
  TestingStatusResponse,
  TestRunConfig,
  TestRunResult,
  TestHistoryResponse,
  CompanyAnswerKey,
} from './testingTypes';

export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/testing`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// =============================================================================
// TESTING API FUNCTIONS
// =============================================================================

export const testingApi = {
  /**
   * Get testing system status and configuration
   */
  async getStatus(): Promise<TestingStatusResponse> {
    const response = await apiClient.get<TestingStatusResponse>('/status');
    return response.data;
  },

  /**
   * Run a test with the given configuration
   * Note: Tests can take several minutes, so we use a long timeout
   */
  async runTest(config: TestRunConfig): Promise<TestRunResult> {
    const response = await apiClient.post<TestRunResult>('/run', config, {
      timeout: 600000, // 10 minutes - tests can take a while
    });
    return response.data;
  },

  /**
   * Get test run history
   */
  async getHistory(limit: number = 50): Promise<TestHistoryResponse> {
    const response = await apiClient.get<TestHistoryResponse>(`/history?limit=${limit}`);
    return response.data;
  },

  /**
   * Get a specific test run result by ID
   */
  async getResult(testId: string): Promise<TestRunResult> {
    const response = await apiClient.get<TestRunResult>(`/result/${testId}`);
    return response.data;
  },

  /**
   * Get the answer key for a specific company
   */
  async getAnswerKey(companyId: string): Promise<CompanyAnswerKey> {
    const response = await apiClient.get<CompanyAnswerKey>(`/answer-key/${companyId}`);
    return response.data;
  },

  /**
   * Update the answer key for a company
   */
  async updateAnswerKey(answerKey: CompanyAnswerKey): Promise<{ success: boolean; message: string }> {
    const response = await apiClient.put<{ success: boolean; message: string }>('/answer-key', answerKey);
    return response.data;
  },

  /**
   * Get the URL for viewing a test file (PDF/Excel)
   */
  getTestFileUrl(filename: string): string {
    // Encode each path segment separately to preserve directory structure
    // This ensures slashes aren't encoded, which FastAPI's path converter handles correctly
    const encodedPath = filename.split('/').map(segment => encodeURIComponent(segment)).join('/');
    return `${API_BASE_URL}/testing/files/${encodedPath}`;
  },
};
