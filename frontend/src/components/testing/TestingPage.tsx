import React, { useState, useEffect, useRef, useCallback } from 'react';
import { ArrowLeft, FlaskConical, RefreshCw, AlertCircle, Wifi, WifiOff } from 'lucide-react';
import { TestConfigPanel } from './TestConfigPanel';
import { TestResultsComparison } from './TestResultsComparison';
import { TestHistoryTable } from './TestHistoryTable';
import { BridgeLoader, TestProgress } from './BridgeLoader';
import { testingApi } from '../../testingApi';
import {
  TestCompany,
  AvailableModel,
  TestRunResult,
  TestRunSummary,
} from '../../testingTypes';
import { connectionManager, ConnectionStatus } from '../../utils/connectionManager';
import { notifyTestComplete, notifyError } from '../../utils/notifications';

interface TestingPageProps {
  onBack: () => void;
}

export const TestingPage: React.FC<TestingPageProps> = ({ onBack }) => {
  // State
  const [status, setStatus] = useState<'loading' | 'idle' | 'running' | 'complete' | 'error'>('loading');
  const [companies, setCompanies] = useState<TestCompany[]>([]);
  const [models, setModels] = useState<AvailableModel[]>([]);
  const [selectedCompany, setSelectedCompany] = useState<TestCompany | undefined>();
  const [selectedModel, setSelectedModel] = useState<AvailableModel | undefined>();
  const [promptContent, setPromptContent] = useState<string>('');
  const [extendedThinking, setExtendedThinking] = useState<boolean>(false);
  const [currentResult, setCurrentResult] = useState<TestRunResult | null>(null);
  const [history, setHistory] = useState<TestRunSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(connectionManager.getStatus());
  const [isManualReconnecting, setIsManualReconnecting] = useState(false);
  const [testProgress, setTestProgress] = useState<TestProgress | null>(null);
  
  // Track if initial load has been attempted
  const initialLoadAttempted = useRef(false);
  const isMounted = useRef(true);
  const wsRef = useRef<WebSocket | null>(null);

  // Subscribe to connection status (connection manager is already started by App.tsx)
  useEffect(() => {
    isMounted.current = true;
    console.log('[TESTING PAGE] Subscribing to connection manager');
    
    const unsubscribe = connectionManager.onStatusChange((status) => {
      if (isMounted.current) {
        setConnectionStatus(status);
      }
    });

    return () => {
      isMounted.current = false;
      console.log('[TESTING PAGE] Unsubscribing from connection manager');
      unsubscribe();
    };
  }, []);

  // Load initial data - only once
  useEffect(() => {
    if (initialLoadAttempted.current) return;
    initialLoadAttempted.current = true;
    
    console.log('[TESTING PAGE] Starting initial data load');
    loadStatus();
    loadHistory();
  }, []);

  // WebSocket connection for test progress updates
  const connectWebSocket = useCallback(() => {
    // Close existing connection if any
    if (wsRef.current && wsRef.current.readyState !== WebSocket.CLOSED) {
      wsRef.current.close();
    }

    // Determine WebSocket URL
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const apiBase = import.meta.env.VITE_API_URL || '';
    let wsUrl: string;
    
    if (apiBase && apiBase.startsWith('http')) {
      // External API URL - convert to WebSocket
      wsUrl = apiBase.replace(/^https?/, wsProtocol.replace(':', '')) + '/ws/progress';
    } else {
      // Same origin
      wsUrl = `${wsProtocol}//${window.location.host}/ws/progress`;
    }

    console.log('[TESTING PAGE] Connecting to WebSocket for progress updates:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[TESTING PAGE] WebSocket connected for progress updates');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Handle test_progress messages
        if (data.type === 'test_progress' && data.payload) {
          console.log('[TESTING PAGE] Progress update:', data.payload);
          if (isMounted.current) {
            setTestProgress(data.payload as TestProgress);
          }
        }
      } catch (e) {
        console.warn('[TESTING PAGE] Failed to parse WebSocket message:', e);
      }
    };

    ws.onerror = (error) => {
      console.error('[TESTING PAGE] WebSocket error:', error);
    };

    ws.onclose = () => {
      console.log('[TESTING PAGE] WebSocket closed');
    };

    return ws;
  }, []);

  // Disconnect WebSocket when not running a test
  const disconnectWebSocket = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      disconnectWebSocket();
    };
  }, [disconnectWebSocket]);

  const loadStatus = async () => {
    console.log('[TESTING PAGE] Loading status...');
    try {
      if (!isMounted.current) return;
      setStatus('loading');
      setError(null);
      
      console.log('[TESTING PAGE] Calling testingApi.getStatus()...');
      const response = await testingApi.getStatus();
      
      // Guard against updates after unmount
      if (!isMounted.current) {
        console.log('[TESTING PAGE] Component unmounted, skipping state update');
        return;
      }
      
      console.log('[TESTING PAGE] Status loaded:', {
        companies: response.available_companies.length,
        models: response.available_models.length,
        hasPromptContent: !!response.current_prompt_content
      });
      
      setCompanies(response.available_companies);
      setModels(response.available_models);
      
      // Set defaults
      if (response.available_companies.length > 0) {
        console.log('[TESTING PAGE] Setting default company:', response.available_companies[0].id);
        setSelectedCompany(response.available_companies[0]);
      }
      if (response.available_models.length > 0) {
        console.log('[TESTING PAGE] Setting default model:', response.available_models[0].id);
        setSelectedModel(response.available_models[0]);
      }
      if (response.current_prompt_content) {
        console.log('[TESTING PAGE] Setting prompt content (length:', response.current_prompt_content.length, ')');
        setPromptContent(response.current_prompt_content);
      }
      
      setStatus('idle');
      console.log('[TESTING PAGE] ✓ Status loaded successfully');
    } catch (err: any) {
      // Guard against updates after unmount
      if (!isMounted.current) return;
      
      console.error('[TESTING PAGE] ❌ Failed to load status:', err.message);
      
      let errorMessage = 'Failed to load testing configuration';
      if (err.code === 'ECONNABORTED') {
        errorMessage = 'Request timed out - backend may be slow or unavailable';
      } else if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
        errorMessage = 'Cannot connect to backend - please ensure the server is running';
      } else if (err.response?.status === 503) {
        errorMessage = 'Testing system is not available on the backend';
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      setStatus('error');
    }
  };

  const loadHistory = async () => {
    console.log('[TESTING PAGE] Loading history...');
    try {
      if (!isMounted.current) return;
      setHistoryLoading(true);
      
      const response = await testingApi.getHistory();
      
      // Guard against updates after unmount
      if (!isMounted.current) return;
      
      console.log('[TESTING PAGE] History loaded:', {
        runs: response.runs.length,
        total: response.total_count
      });
      setHistory(response.runs);
    } catch (err: any) {
      if (!isMounted.current) return;
      console.error('[TESTING PAGE] ❌ Failed to load history:', err.message);
      // Don't set error state for history - just log it
    } finally {
      if (isMounted.current) {
        setHistoryLoading(false);
      }
    }
  };

  const handleRunTest = async () => {
    if (!selectedCompany || !selectedModel) {
      console.error('[TESTING PAGE] Cannot run test - missing company or model');
      return;
    }

    console.log('[TESTING PAGE] ═══════════════════════════════════════════════');
    console.log('[TESTING PAGE] STARTING TEST RUN');
    console.log('[TESTING PAGE] Company:', selectedCompany.id, '-', selectedCompany.name);
    console.log('[TESTING PAGE] Model:', selectedModel.id, '-', selectedModel.name);
    console.log('[TESTING PAGE] Prompt Override:', promptContent ? `Yes (${promptContent.length} chars)` : 'No');
    console.log('[TESTING PAGE] ═══════════════════════════════════════════════');

    try {
      setStatus('running');
      setError(null);
      setCurrentResult(null);
      setTestProgress(null);

      // Connect WebSocket for progress updates
      connectWebSocket();

      const config = {
        company_id: selectedCompany.id,
        model_name: selectedModel.id,
        prompt_override: promptContent || undefined,
        extended_thinking: extendedThinking,
      };
      
      console.log('[TESTING PAGE] Calling testingApi.runTest()...', config);
      const startTime = Date.now();
      
      const result = await testingApi.runTest(config);
      
      const duration = Date.now() - startTime;
      console.log('[TESTING PAGE] ═══════════════════════════════════════════════');
      console.log('[TESTING PAGE] ✓ TEST RUN COMPLETE');
      console.log('[TESTING PAGE] Test ID:', result.id);
      console.log('[TESTING PAGE] Score:', result.overall_score.toFixed(1) + '%');
      console.log('[TESTING PAGE] Grade:', result.overall_grade);
      console.log('[TESTING PAGE] Files:', result.total_files);
      console.log('[TESTING PAGE] Periods:', result.total_periods);
      console.log('[TESTING PAGE] Fields Correct:', result.fields_correct);
      console.log('[TESTING PAGE] Fields Wrong:', result.fields_wrong);
      console.log('[TESTING PAGE] Fields Missing:', result.fields_missing);
      console.log('[TESTING PAGE] Backend Time:', result.execution_time_seconds.toFixed(2) + 's');
      console.log('[TESTING PAGE] Total Time:', (duration / 1000).toFixed(2) + 's');
      console.log('[TESTING PAGE] ═══════════════════════════════════════════════');

      setCurrentResult(result);
      setStatus('complete');
      
      // Show completion notification
      notifyTestComplete(
        selectedCompany.name,
        result.overall_score,
        result.overall_grade,
        result.execution_time_seconds
      );
      
      // Disconnect WebSocket after a short delay to show final progress
      setTimeout(() => {
        disconnectWebSocket();
        setTestProgress(null);
      }, 2000);
      
      // Refresh history
      console.log('[TESTING PAGE] Refreshing history...');
      loadHistory();
    } catch (err: any) {
      console.error('[TESTING PAGE] ═══════════════════════════════════════════════');
      console.error('[TESTING PAGE] ❌ TEST RUN FAILED');
      console.error('[TESTING PAGE] Error:', err.message);
      console.error('[TESTING PAGE] Error Code:', err.code);
      console.error('[TESTING PAGE] Response Data:', err.response?.data);
      console.error('[TESTING PAGE] Response Status:', err.response?.status);
      console.error('[TESTING PAGE] ═══════════════════════════════════════════════');
      
      let errorMessage = err.message || 'Test run failed';
      
      if (err.code === 'ECONNABORTED') {
        errorMessage = 'Request timed out - backend may be disconnected or test is taking too long';
      } else if (err.code === 'ERR_NETWORK') {
        errorMessage = 'Network error - backend appears to be disconnected or down';
      } else if (err.response?.status === 500) {
        errorMessage = `Internal server error: ${err.response.data?.detail || 'Unknown error'}`;
      } else if (err.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      }
      
      setError(errorMessage);
      setStatus('error');
      
      // Show error notification
      notifyError('Test Run Failed', errorMessage);
      
      // Disconnect WebSocket on error
      disconnectWebSocket();
      setTestProgress(null);
    }
  };

  const handleViewResult = async (testId: string) => {
    console.log('[TESTING PAGE] Loading test result:', testId);
    try {
      setStatus('loading');
      const result = await testingApi.getResult(testId);
      console.log('[TESTING PAGE] ✓ Test result loaded:', {
        testId: result.id,
        score: result.overall_score,
        files: result.total_files
      });
      setCurrentResult(result);
      setStatus('complete');
    } catch (err: any) {
      console.error('[TESTING PAGE] ❌ Failed to load test result:', err);
      setError(err.message || 'Failed to load test result');
      setStatus('error');
    }
  };

  const handleClearResult = () => {
    console.log('[TESTING PAGE] Clearing current result');
    setCurrentResult(null);
    setStatus('idle');
  };

  const handleManualReconnect = async () => {
    console.log('[TESTING PAGE] Manual reconnect triggered');
    setIsManualReconnecting(true);
    try {
      await connectionManager.reconnect();
    } finally {
      setIsManualReconnecting(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-80px)] bg-gradient-to-br from-violet-50/50 via-white to-purple-50/50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-[73px] z-30">
        <div className="max-w-[95%] mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={onBack}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span className="font-medium">Back</span>
              </button>
              <div className="h-6 w-px bg-gray-300" />
              <div className="flex items-center gap-2">
                <div className="bg-gradient-to-br from-violet-500 to-purple-600 p-2 rounded-lg">
                  <FlaskConical className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Testing Lab</h2>
                  <p className="text-xs text-gray-500">Evaluate extraction accuracy against answer keys</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Connection Status Indicator */}
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
                connectionStatus.state === 'reconnecting'
                  ? 'bg-yellow-50 text-yellow-700'
                  : connectionStatus.state === 'connected'
                    ? 'bg-green-50 text-green-700' 
                    : connectionStatus.state === 'degraded'
                      ? 'bg-amber-50 text-amber-700'
                      : 'bg-red-50 text-red-700'
              }`}>
                {connectionStatus.state === 'reconnecting' ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span className="font-medium">Reconnecting...</span>
                    {connectionStatus.reconnectAttempt > 0 && (
                      <span className="text-xs opacity-70">(attempt {connectionStatus.reconnectAttempt})</span>
                    )}
                  </>
                ) : connectionStatus.state === 'connected' ? (
                  <>
                    <Wifi className="w-4 h-4" />
                    <span className="font-medium">Connected</span>
                    {connectionStatus.latencyMs && (
                      <span className="text-xs opacity-70">({connectionStatus.latencyMs}ms)</span>
                    )}
                  </>
                ) : connectionStatus.state === 'degraded' ? (
                  <>
                    <Wifi className="w-4 h-4" />
                    <span className="font-medium">Degraded</span>
                    <span className="text-xs opacity-70">(WS reconnecting)</span>
                  </>
                ) : (
                  <>
                    <WifiOff className="w-4 h-4" />
                    <span className="font-medium">Disconnected</span>
                    {connectionStatus.error && (
                      <span className="text-xs opacity-70" title={connectionStatus.error}>
                        ({connectionStatus.error})
                      </span>
                    )}
                  </>
                )}
              </div>

              {/* Reconnect button - show when not fully connected */}
              {connectionStatus.state !== 'connected' && connectionStatus.state !== 'reconnecting' && (
                <button
                  onClick={handleManualReconnect}
                  disabled={isManualReconnecting}
                  className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-lg transition-colors border ${
                    isManualReconnecting
                      ? 'text-gray-400 border-gray-200 cursor-not-allowed'
                      : 'text-red-600 hover:text-red-700 hover:bg-red-50 border-red-200'
                  }`}
                  title="Retry connection"
                >
                  <RefreshCw className={`w-4 h-4 ${isManualReconnecting ? 'animate-spin' : ''}`} />
                  {isManualReconnecting ? 'Reconnecting...' : 'Reconnect'}
                </button>
              )}
              
              <button
                onClick={loadHistory}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-[95%] mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {status === 'running' && <BridgeLoader progress={testProgress} />}
        {status === 'loading' && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-12 h-12 border-3 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto" />
              <p className="text-gray-600 mt-4">Loading testing system...</p>
            </div>
          </div>
        )}

        {status === 'error' && !currentResult && (
          <div className="max-w-lg mx-auto py-20">
            <div className="bg-white border border-red-200 rounded-2xl p-8 text-center">
              <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-red-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Error</h3>
              <p className="text-gray-600 mb-6">{error}</p>
              <button
                onClick={loadStatus}
                className="px-6 py-2.5 bg-violet-600 text-white rounded-xl hover:bg-violet-700 transition-colors font-medium"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {(status === 'idle' || status === 'running') && !currentResult && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Config Panel */}
            <div className="lg:col-span-1">
              <TestConfigPanel
                companies={companies}
                models={models}
                selectedCompany={selectedCompany}
                selectedModel={selectedModel}
                promptContent={promptContent}
                extendedThinking={extendedThinking}
                onSelectCompany={setSelectedCompany}
                onSelectModel={setSelectedModel}
                onPromptChange={setPromptContent}
                onExtendedThinkingChange={setExtendedThinking}
                onRunTest={handleRunTest}
                isRunning={status === 'running'}
              />
            </div>

            {/* History */}
            <div className="lg:col-span-3">
              <TestHistoryTable
                history={history}
                onViewResult={handleViewResult}
                isLoading={historyLoading}
              />
            </div>
          </div>
        )}

        {(status === 'complete' || (status === 'error' && currentResult)) && currentResult && (
          <div className="space-y-6">
            {/* Action Bar */}
            <div className="flex items-center justify-between">
              <button
                onClick={handleClearResult}
                className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span className="font-medium">Back to Configuration</span>
              </button>

              <button
                onClick={handleRunTest}
                className="flex items-center gap-2 px-4 py-2 bg-violet-600 text-white rounded-lg hover:bg-violet-700 transition-colors font-medium"
              >
                <RefreshCw className="w-4 h-4" />
                Run Again
              </button>
            </div>

            {/* Results */}
            <TestResultsComparison result={currentResult} />

            {/* History Below */}
            <div className="mt-8">
              <TestHistoryTable
                history={history}
                onViewResult={handleViewResult}
                isLoading={historyLoading}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TestingPage;
