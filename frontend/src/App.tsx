import { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { UploadPage } from './components/UploadPage';
import { SpreadingView } from './components/SpreadingView';
import { DebugPanel } from './components/DebugPanel';
import { api, wsManager } from './api';
import { 
  SpreadResponse, 
  DocType, 
  FileUploadItem, 
  LogEntry, 
  ProcessingStep, 
  WebSocketMessage,
  BatchSpreadResponse 
} from './types';
import { AlertCircle, FileText, CheckCircle, XCircle, ArrowLeft, Power } from 'lucide-react';

interface SingleResult {
  result: SpreadResponse;
  docType: DocType;
}

interface BatchResultItem {
  filename: string;
  success: boolean;
  result?: SpreadResponse;
  docType: DocType;
  error?: string;
}

type AppState = 
  | { status: 'upload' }
  | { status: 'processing'; files: FileUploadItem[] }
  | { status: 'success'; mode: 'single'; data: SingleResult }
  | { status: 'success'; mode: 'batch'; data: BatchResultItem[]; selectedIndex: number }
  | { status: 'error'; error: string };

function App() {
  const [state, setState] = useState<AppState>({ status: 'upload' });
  const [debugOpen, setDebugOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [steps, setSteps] = useState<ProcessingStep[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [startingBackend, setStartingBackend] = useState(false);
  const logIdCounter = useRef(0);

  // Connect to WebSocket on mount
  useEffect(() => {
    wsManager.connect();

    const unsubMessage = wsManager.onMessage((message: WebSocketMessage) => {
      handleWebSocketMessage(message);
    });

    const unsubConnection = wsManager.onConnectionChange((connected) => {
      setWsConnected(connected);
      if (connected) {
        addLocalLog('info', 'Connected to server');
      } else {
        addLocalLog('warning', 'Disconnected from server');
      }
    });

    return () => {
      unsubMessage();
      unsubConnection();
      wsManager.disconnect();
    };
  }, []);

  const addLocalLog = useCallback((level: LogEntry['level'], message: string, details?: Record<string, unknown>) => {
    const entry: LogEntry = {
      id: `local-${logIdCounter.current++}`,
      timestamp: new Date().toISOString(),
      level,
      message,
      source: 'frontend',
      details,
    };
    setLogs(prev => [...prev, entry]);
  }, []);

  const handleWebSocketMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'log':
        const logPayload = message.payload as LogEntry;
        setLogs(prev => {
          // Avoid duplicates
          if (prev.some(l => l.id === logPayload.id)) return prev;
          return [...prev, logPayload];
        });
        
        // Auto-open debug panel on errors
        if (logPayload.level === 'error') {
          setDebugOpen(true);
        }
        break;

      case 'step':
        const stepPayload = message.payload as ProcessingStep;
        setSteps(prev => {
          const existing = prev.findIndex(s => s.id === stepPayload.id);
          if (existing >= 0) {
            const updated = [...prev];
            updated[existing] = stepPayload;
            return updated;
          }
          return [...prev, stepPayload];
        });
        break;

      case 'progress':
        // Handle batch progress updates
        const progress = message.payload as { current?: number; total?: number; status?: string };
        if (progress.current && progress.total) {
          addLocalLog('info', `Processing file ${progress.current}/${progress.total}`);
        }
        break;

      case 'error':
        const errorPayload = message.payload as { message?: string };
        addLocalLog('error', errorPayload.message || 'Unknown error occurred');
        setDebugOpen(true);
        break;
    }
  }, [addLocalLog]);

  const handleUpload = async (files: FileUploadItem[]) => {
    // Clear previous steps
    setSteps([]);
    
    // Update files to processing state
    const processingFiles = files.map((f, idx) => ({
      ...f,
      status: idx === 0 ? 'processing' : 'pending',
    } as FileUploadItem));
    
    setState({ status: 'processing', files: processingFiles });
    addLocalLog('info', `Starting processing of ${files.length} file(s)`, {
      filenames: files.map(f => f.file.name)
    });

    try {
      if (files.length === 1) {
        // Single file processing
        const file = files[0];
        const result = await api.spreadFinancialStatement({
          file: file.file,
          doc_type: file.docType,
        });

        if (result.success && result.data) {
          addLocalLog('info', 'Processing completed successfully');
          setState({ 
            status: 'success', 
            mode: 'single',
            data: { result, docType: file.docType }
          });
        } else {
          addLocalLog('error', result.error || 'Unknown error occurred');
          setState({ 
            status: 'error', 
            error: result.error || 'Unknown error occurred' 
          });
          setDebugOpen(true);
        }
      } else {
        // Batch processing
        const batchResult = await api.spreadBatch(files);
        
        addLocalLog('info', `Batch processing complete: ${batchResult.completed}/${batchResult.total_files} successful`);
        
        const results: BatchResultItem[] = batchResult.results.map((r, idx) => ({
          filename: r.filename,
          success: r.success,
          docType: files[idx].docType,
          result: r.success ? {
            success: true,
            job_id: r.job_id || '',
            data: r.data || null,
            metadata: r.metadata || {
              total_fields: 0,
              high_confidence: 0,
              medium_confidence: 0,
              low_confidence: 0,
              missing: 0,
              extraction_rate: 0,
              average_confidence: 0,
              original_filename: r.filename,
              job_id: r.job_id || '',
              pdf_url: ''
            }
          } : undefined,
          error: r.error
        }));

        if (batchResult.completed > 0) {
          // Find first successful result as default selection
          const firstSuccessIdx = results.findIndex(r => r.success);
          setState({ 
            status: 'success', 
            mode: 'batch',
            data: results,
            selectedIndex: firstSuccessIdx >= 0 ? firstSuccessIdx : 0
          });
        } else {
          addLocalLog('error', 'All files failed to process');
          setState({ 
            status: 'error', 
            error: 'All files failed to process. Check the debug panel for details.' 
          });
          setDebugOpen(true);
        }
      }
    } catch (error: any) {
      console.error('Error spreading financial statement:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Failed to process document';
      addLocalLog('error', errorMessage, {
        stack: error.stack,
        response: error.response?.data
      });
      setState({ 
        status: 'error', 
        error: errorMessage
      });
      setDebugOpen(true);
    }
  };

  const handleBack = () => {
    setSteps([]);
    setState({ status: 'upload' });
  };

  const handleClearLogs = () => {
    setLogs([]);
    setSteps([]);
  };

  const handleStartBackend = async () => {
    setStartingBackend(true);
    try {
      const result = await api.startBackend();
      if (result.success) {
        addLocalLog('info', 'Backend startup initiated. Waiting for connection...');
        // Try to reconnect after a short delay
        setTimeout(() => {
          wsManager.connect();
        }, 2000);
      } else {
        addLocalLog('error', result.message || 'Failed to start backend');
      }
    } catch (error: any) {
      console.error('Failed to start backend:', error);
      addLocalLog('error', `Failed to start backend: ${error.message || 'Startup service may not be running'}`);
    } finally {
      setStartingBackend(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50/30">
      <Header />

      {state.status === 'upload' && (
        <UploadPage 
          onUpload={handleUpload} 
          isProcessing={false} 
        />
      )}

      {state.status === 'processing' && (
        <UploadPage 
          onUpload={handleUpload} 
          isProcessing={true}
          processingFiles={state.files}
        />
      )}

      {state.status === 'success' && state.mode === 'single' && state.data.result.data && (
        <SpreadingView
          data={state.data.result.data}
          metadata={state.data.result.metadata}
          docType={state.data.docType}
          onBack={handleBack}
        />
      )}

      {state.status === 'success' && state.mode === 'batch' && (
        <BatchResultsView
          results={state.data}
          selectedIndex={state.selectedIndex}
          onSelectIndex={(idx) => setState({ ...state, selectedIndex: idx })}
          onBack={handleBack}
        />
      )}

      {state.status === 'error' && (
        <div className="min-h-[calc(100vh-80px)] flex items-center justify-center p-8">
          <div className="max-w-lg w-full bg-white border border-red-200 rounded-2xl p-8 shadow-lg shadow-red-500/5">
            <div className="flex flex-col items-center text-center">
              <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mb-4">
                <AlertCircle className="w-8 h-8 text-red-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">
                Processing Failed
              </h3>
              <p className="text-gray-600 mb-6 max-w-md">
                {state.error}
              </p>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleBack}
                  className="px-6 py-2.5 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors font-medium"
                >
                  Try Again
                </button>
                <button
                  onClick={() => setDebugOpen(true)}
                  className="px-6 py-2.5 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors font-medium"
                >
                  View Debug Logs
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Debug Panel */}
      <DebugPanel
        isOpen={debugOpen}
        onToggle={() => setDebugOpen(!debugOpen)}
        logs={logs}
        steps={steps}
        onClear={handleClearLogs}
      />

      {/* WebSocket Connection Indicator */}
      <div className="fixed bottom-6 left-6 flex items-center gap-2">
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
          wsConnected 
            ? 'bg-emerald-100 text-emerald-700' 
            : 'bg-amber-100 text-amber-700'
        }`}>
          <span className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`} />
          {wsConnected ? 'Connected' : 'Reconnecting...'}
        </div>
        {!wsConnected && (
          <button
            onClick={handleStartBackend}
            disabled={startingBackend}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
              startingBackend
                ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
                : 'bg-blue-100 text-blue-700 hover:bg-blue-200'
            }`}
            title="Start Backend Server"
          >
            <Power className={`w-3 h-3 ${startingBackend ? 'animate-spin' : ''}`} />
            {startingBackend ? 'Starting...' : 'Start Backend'}
          </button>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// BATCH RESULTS VIEW COMPONENT
// =============================================================================

interface BatchResultsViewProps {
  results: BatchResultItem[];
  selectedIndex: number;
  onSelectIndex: (index: number) => void;
  onBack: () => void;
}

const BatchResultsView: React.FC<BatchResultsViewProps> = ({
  results,
  selectedIndex,
  onSelectIndex,
  onBack,
}) => {
  const selectedResult = results[selectedIndex];
  const successCount = results.filter(r => r.success).length;
  const failCount = results.filter(r => !r.success).length;

  return (
    <div className="min-h-[calc(100vh-80px)]">
      {/* Results Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onBack}
              className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              <span className="font-medium">Back</span>
            </button>
            <div className="h-6 w-px bg-gray-300" />
            <h2 className="text-lg font-semibold text-gray-900">
              Batch Results
            </h2>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="flex items-center gap-1.5 text-emerald-600">
              <CheckCircle className="w-4 h-4" />
              {successCount} successful
            </span>
            {failCount > 0 && (
              <span className="flex items-center gap-1.5 text-red-600">
                <XCircle className="w-4 h-4" />
                {failCount} failed
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        <div className="flex gap-6">
          {/* File List Sidebar */}
          <div className="w-72 flex-shrink-0">
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                <h3 className="font-medium text-gray-900">Processed Files</h3>
              </div>
              <div className="divide-y divide-gray-100 max-h-[600px] overflow-y-auto">
                {results.map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => onSelectIndex(idx)}
                    className={`w-full px-4 py-3 flex items-center gap-3 text-left transition-colors ${
                      idx === selectedIndex 
                        ? 'bg-emerald-50 border-l-2 border-emerald-500' 
                        : 'hover:bg-gray-50 border-l-2 border-transparent'
                    }`}
                  >
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      item.success ? 'bg-emerald-100' : 'bg-red-100'
                    }`}>
                      {item.success ? (
                        <CheckCircle className="w-4 h-4 text-emerald-600" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-600" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-gray-900 truncate text-sm">
                        {item.filename}
                      </p>
                      <p className={`text-xs ${
                        item.success ? 'text-emerald-600' : 'text-red-600'
                      }`}>
                        {item.success 
                          ? `${item.docType === 'income' ? 'Income Statement' : 'Balance Sheet'}`
                          : 'Failed'
                        }
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Selected Result Detail */}
          <div className="flex-1">
            {selectedResult.success && selectedResult.result?.data ? (
              <SpreadingView
                data={selectedResult.result.data}
                metadata={selectedResult.result.metadata}
                docType={selectedResult.docType}
                onBack={onBack}
                hideBackButton
                title={selectedResult.filename}
              />
            ) : (
              <div className="bg-white rounded-xl border border-red-200 p-8">
                <div className="flex flex-col items-center text-center">
                  <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mb-4">
                    <XCircle className="w-8 h-8 text-red-600" />
                  </div>
                  <h3 className="text-lg font-bold text-gray-900 mb-2">
                    Failed to Process
                  </h3>
                  <p className="text-gray-600 max-w-md">
                    {selectedResult.error || 'Unknown error occurred'}
                  </p>
                  <p className="text-sm text-gray-500 mt-4">
                    Check the debug panel for more details
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
