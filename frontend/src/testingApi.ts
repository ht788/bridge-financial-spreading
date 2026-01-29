/**
 * API client for the Bridge Financial Spreader Testing System
 */

import axios from 'axios';
import {
  TestingStatusResponse,
  TestRunConfig,
  TestRunResult,
  TestHistoryResponse,
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
   */
  async runTest(config: TestRunConfig): Promise<TestRunResult> {
    const response = await apiClient.post<TestRunResult>('/run', config);
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
};
