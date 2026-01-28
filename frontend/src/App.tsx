import { useState, useEffect, useCallback, useRef } from 'react';
import { Header } from './components/Header';
import { UploadPage } from './components/UploadPage';
import { SpreadingView } from './components/SpreadingView';
import { DebugPanel } from './components/DebugPanel';
import { TestingPage } from './components/testing/TestingPage';
import { api } from './api';
import { connectionManager, ConnectionStatus, WebSocketMessage as CMWebSocketMessage } from './utils/connectionManager';
import { 
  SpreadResponse, 
  DocType, 
  FileUploadItem, 
  LogEntry, 
  ProcessingStep,
  MultiPeriodIncomeStatement,
  MultiPeriodBalanceSheet,
  FinancialStatement,
  isMultiPeriod,
  CombinedFinancialExtraction,
  isCombinedExtraction,
  SpreadMetadata
} from './types';
import { UploadOptions } from './components/UploadPage';
import { AlertCircle, CheckCircle, XCircle, ArrowLeft, RefreshCw, Wifi, WifiOff, Layers, FileText, Loader2 } from 'lucide-react';

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

type PageType = 'home' | 'testing';

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>('home');
  const [state, setState] = useState<AppState>({ status: 'upload' });
  const [debugOpen, setDebugOpen] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [steps, setSteps] = useState<ProcessingStep[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(connectionManager.getStatus());
  const [isReconnecting, setIsReconnecting] = useState(false);
  const logIdCounter = useRef(0);
  const lastConnectionState = useRef<string | null>(null);

  // Connect to backend on mount using unified connection manager
  useEffect(() => {
    connectionManager.start();

    const unsubMessage = connectionManager.onMessage((message: CMWebSocketMessage) => {
      handleWebSocketMessage(message);
    });

    const unsubStatus = connectionManager.onStatusChange((status) => {
      setConnectionStatus(status);
      
      // Log connection state changes (but not every status update)
      if (lastConnectionState.current !== status.state) {
        lastConnectionState.current = status.state;
        
        switch (status.state) {
          case 'connected':
            addLocalLog('info', 'Connected to server');
            break;
          case 'degraded':
            addLocalLog('warning', 'Connection degraded - WebSocket disconnected');
            break;
          case 'reconnecting':
            if (status.reconnectAttempt === 1) {
              addLocalLog('warning', 'Connection lost - attempting to reconnect...');
            }
            break;
          case 'disconnected':
            addLocalLog('error', `Backend unavailable: ${status.error || 'Unknown error'}`);
            break;
        }
      }
    });

    return () => {
      unsubMessage();
      unsubStatus();
      connectionManager.stop();
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

  const handleWebSocketMessage = useCallback((message: CMWebSocketMessage) => {
    switch (message.type) {
      case 'log': {
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
      }

      case 'step': {
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
      }

      case 'progress': {
        // Handle batch progress updates
        const progress = message.payload as { current?: number; total?: number; status?: string };
        if (progress.current && progress.total) {
          addLocalLog('info', `Processing file ${progress.current}/${progress.total}`);
        }
        break;
      }

      case 'error': {
        const errorPayload = message.payload as { message?: string };
        addLocalLog('error', errorPayload.message || 'Unknown error occurred');
        setDebugOpen(true);
        break;
      }
    }
  }, [addLocalLog]);

  const handleUpload = async (files: FileUploadItem[], options?: UploadOptions) => {
    // Clear previous steps
    setSteps([]);
    
    // Pause health checks during processing to avoid misleading "Backend unavailable" messages
    // The backend may be slow to respond to health checks while processing large PDFs
    connectionManager.pauseHealthChecks();
    
    // Update files to processing state
    const processingFiles = files.map((f, idx) => ({
      ...f,
      status: idx === 0 ? 'processing' : 'pending',
    } as FileUploadItem));
    
    setState({ status: 'processing', files: processingFiles });
    addLocalLog('info', `Starting processing of ${files.length} file(s)`, {
      filenames: files.map(f => f.file.name),
      model: options?.modelOverride || 'default'
    });

    try {
      if (files.length === 1) {
        // Single file processing
        const file = files[0];
        const result = await api.spreadFinancialStatement({
          file: file.file,
          doc_type: file.docType,
          model_override: options?.modelOverride,
          extended_thinking: options?.extendedThinking,
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
        const batchResult = await api.spreadBatch(files, {
          model_override: options?.modelOverride,
          extended_thinking: options?.extendedThinking,
        });
        
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
    } finally {
      // Resume health checks now that processing is complete
      connectionManager.resumeHealthChecks();
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

  const handleReconnect = async () => {
    setIsReconnecting(true);
    addLocalLog('info', 'Manual reconnect initiated...');
    try {
      await connectionManager.reconnect();
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Unknown error';
      console.error('Reconnect failed:', error);
      addLocalLog('error', `Reconnect failed: ${message}`);
    } finally {
      setIsReconnecting(false);
    }
  };

  const handleNavigateToTesting = () => {
    setCurrentPage('testing');
  };

  const handleNavigateToHome = () => {
    setCurrentPage('home');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50/30">
      <Header 
        onNavigateToTesting={handleNavigateToTesting}
        onNavigateToHome={handleNavigateToHome}
        currentPage={currentPage}
      />

      {/* Testing Page */}
      {currentPage === 'testing' && (
        <TestingPage onBack={handleNavigateToHome} />
      )}

      {/* Home Page Content */}
      {currentPage === 'home' && state.status === 'upload' && (
        <UploadPage 
          onUpload={handleUpload} 
          isProcessing={false} 
        />
      )}

      {currentPage === 'home' && state.status === 'processing' && (
        <UploadPage 
          onUpload={handleUpload} 
          isProcessing={true}
          processingFiles={state.files}
        />
      )}

      {currentPage === 'home' && state.status === 'success' && state.mode === 'single' && state.data.result.data && (
        <SpreadingView
          data={state.data.result.data}
          metadata={state.data.result.metadata}
          docType={state.data.docType}
          onBack={handleBack}
        />
      )}

      {currentPage === 'home' && state.status === 'success' && state.mode === 'batch' && (
        <BatchResultsView
          results={state.data}
          selectedIndex={state.selectedIndex}
          onSelectIndex={(idx) => setState({ ...state, selectedIndex: idx })}
          onBack={handleBack}
        />
      )}

      {currentPage === 'home' && state.status === 'error' && (
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

      {/* Connection Status Indicator */}
      <ConnectionIndicator 
        status={connectionStatus} 
        onReconnect={handleReconnect}
        isReconnecting={isReconnecting}
        isProcessing={state.status === 'processing'}
      />
    </div>
  );
}

// =============================================================================
// CONNECTION INDICATOR COMPONENT
// =============================================================================

interface ConnectionIndicatorProps {
  status: ConnectionStatus;
  onReconnect: () => void;
  isReconnecting: boolean;
  isProcessing: boolean;
}

const ConnectionIndicator: React.FC<ConnectionIndicatorProps> = ({
  status,
  onReconnect,
  isReconnecting,
  isProcessing,
}) => {
  const getStatusConfig = () => {
    // If actively processing, show a special "processing" state instead of connection errors
    // This prevents confusing "Backend unavailable" messages while the backend is working
    if (isProcessing) {
      return {
        bgColor: 'bg-blue-100',
        textColor: 'text-blue-700',
        dotColor: 'bg-blue-500',
        icon: <Loader2 className="w-3 h-3 animate-spin" />,
        label: 'Processing files...',
        showReconnect: false,
        animate: true,
      };
    }
    
    switch (status.state) {
      case 'connected':
        return {
          bgColor: 'bg-emerald-100',
          textColor: 'text-emerald-700',
          dotColor: 'bg-emerald-500',
          icon: <Wifi className="w-3 h-3" />,
          label: status.latencyMs ? `Connected (${status.latencyMs}ms)` : 'Connected',
          showReconnect: false,
          animate: false,
        };
      case 'degraded':
        return {
          bgColor: 'bg-amber-100',
          textColor: 'text-amber-700',
          dotColor: 'bg-amber-500',
          icon: <Wifi className="w-3 h-3" />,
          label: 'Degraded - WS reconnecting',
          showReconnect: true,
          animate: true,
        };
      case 'reconnecting':
        return {
          bgColor: 'bg-amber-100',
          textColor: 'text-amber-700',
          dotColor: 'bg-amber-500',
          icon: <RefreshCw className="w-3 h-3 animate-spin" />,
          label: status.reconnectAttempt > 0 
            ? `Reconnecting (attempt ${status.reconnectAttempt})...` 
            : 'Reconnecting...',
          showReconnect: true,
          animate: true,
        };
      case 'disconnected':
        return {
          bgColor: 'bg-red-100',
          textColor: 'text-red-700',
          dotColor: 'bg-red-500',
          icon: <WifiOff className="w-3 h-3" />,
          label: 'Disconnected',
          showReconnect: true,
          animate: false,
        };
    }
  };

  const config = getStatusConfig();

  return (
    <div className="fixed bottom-6 left-6 flex items-center gap-2">
      <div 
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${config.bgColor} ${config.textColor}`}
        title={status.error || undefined}
      >
        <span className={`w-2 h-2 rounded-full ${config.dotColor} ${config.animate ? 'animate-pulse' : ''}`} />
        {config.icon}
        <span>{config.label}</span>
      </div>
      
      {config.showReconnect && (
        <button
          onClick={onReconnect}
          disabled={isReconnecting}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
            isReconnecting
              ? 'bg-gray-100 text-gray-500 cursor-not-allowed'
              : 'bg-blue-100 text-blue-700 hover:bg-blue-200 active:bg-blue-300'
          }`}
          title={status.error ? `Last error: ${status.error}` : 'Click to reconnect'}
        >
          <RefreshCw className={`w-3 h-3 ${isReconnecting ? 'animate-spin' : ''}`} />
          {isReconnecting ? 'Reconnecting...' : 'Reconnect'}
        </button>
      )}
      
      {/* Show next retry countdown for reconnecting state */}
      {status.state === 'reconnecting' && status.nextReconnectMs && status.nextReconnectMs > 2000 && (
        <span className="text-xs text-gray-500">
          Next try in {Math.ceil(status.nextReconnectMs / 1000)}s
        </span>
      )}
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

const aggregateBatchResults = (results: BatchResultItem[], docType: 'income' | 'balance') => {
  const validResults = results.filter(r => r.success && r.result?.data);
  if (validResults.length === 0) return null;

  const periods: any[] = [];
  let currency = 'USD';
  let scale = 'units';

  validResults.forEach(r => {
    const data = r.result!.data;
    const metadata = r.result!.metadata;
    
    // Handle CombinedFinancialExtraction (auto-detect)
    if (isCombinedExtraction(data)) {
       const combined = data as CombinedFinancialExtraction;
       if (docType === 'income' && combined.income_statement) {
         combined.income_statement.periods.forEach(p => {
           periods.push({ ...p, pdf_url: metadata.pdf_url, original_filename: r.filename });
         });
         if (combined.income_statement.currency) currency = combined.income_statement.currency;
         if (combined.income_statement.scale) scale = combined.income_statement.scale;
       } else if (docType === 'balance' && combined.balance_sheet) {
         combined.balance_sheet.periods.forEach(p => {
           periods.push({ ...p, pdf_url: metadata.pdf_url, original_filename: r.filename });
         });
         if (combined.balance_sheet.currency) currency = combined.balance_sheet.currency;
         if (combined.balance_sheet.scale) scale = combined.balance_sheet.scale;
       }
    } 
    // Handle MultiPeriodFinancialStatement
    else if (isMultiPeriod(data)) {
       // Check if it matches requested type (simple check)
       const isIncome = 'revenue' in (data.periods[0] as any).data;
       if ((docType === 'income' && isIncome) || (docType === 'balance' && !isIncome)) {
          data.periods.forEach(p => {
            periods.push({ ...p, pdf_url: metadata.pdf_url, original_filename: r.filename });
          });
          if (data.currency) currency = data.currency;
          if (data.scale) scale = data.scale;
       }
    }
    // Handle Single Period
    else {
       const singleData = data as FinancialStatement;
       const isIncome = 'revenue' in singleData;
       
       if ((docType === 'income' && isIncome) || (docType === 'balance' && !isIncome)) {
          periods.push({
            period_label: (singleData as any).fiscal_period || (singleData as any).as_of_date || r.filename,
            end_date: (singleData as any).as_of_date,
            data: singleData,
            pdf_url: metadata.pdf_url,
            original_filename: r.filename
          });
          if (singleData.currency) currency = singleData.currency;
          if (singleData.scale) scale = singleData.scale;
       }
    }
  });

  if (periods.length === 0) return null;

  return {
    periods,
    currency,
    scale
  };
};

const BatchResultsView: React.FC<BatchResultsViewProps> = ({
  results,
  selectedIndex,
  onSelectIndex,
  onBack,
}) => {
  const [viewMode, setViewMode] = useState<'combined' | 'individual'>('combined');
  const [combinedType, setCombinedType] = useState<'income' | 'balance'>('income');

  const selectedResult = results[selectedIndex];
  const successCount = results.filter(r => r.success).length;
  const failCount = results.filter(r => !r.success).length;

  // Aggregate results
  const combinedIncome = aggregateBatchResults(results, 'income');
  const combinedBalance = aggregateBatchResults(results, 'balance');

  // Determine available combined types
  const hasIncome = combinedIncome !== null;
  const hasBalance = combinedBalance !== null;

  // Auto-select available type if current selection is invalid
  useEffect(() => {
    if (combinedType === 'income' && !hasIncome && hasBalance) {
      setCombinedType('balance');
    } else if (combinedType === 'balance' && !hasBalance && hasIncome) {
      setCombinedType('income');
    }
  }, [hasIncome, hasBalance, combinedType]);

  const renderCombinedView = () => {
    const data = combinedType === 'income' ? combinedIncome : combinedBalance;
    
    if (!data) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-12 text-gray-500">
          <Layers className="w-12 h-12 mb-4 text-gray-300" />
          <p className="text-lg font-medium">No {combinedType} statements found in batch results.</p>
        </div>
      );
    }

    // Create synthetic metadata for combined view
    const syntheticMetadata: SpreadMetadata = {
      total_fields: 0, // Placeholder
      high_confidence: 0,
      medium_confidence: 0,
      low_confidence: 0,
      missing: 0,
      extraction_rate: 0,
      average_confidence: 0,
      original_filename: "Combined View",
      job_id: "batch-combined",
      pdf_url: data.periods[0]?.pdf_url || "", // Default to first PDF
      parallel_extraction: false
    };

    return (
      <SpreadingView
        data={data as any}
        metadata={syntheticMetadata}
        docType={combinedType}
        onBack={onBack}
        hideBackButton
        title="Combined Financial Statements"
      />
    );
  };

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
            
            {/* View Mode Toggle */}
            <div className="flex items-center bg-gray-100 rounded-lg p-1 ml-4">
              <button
                onClick={() => setViewMode('combined')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  viewMode === 'combined' 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Combined View
              </button>
              <button
                onClick={() => setViewMode('individual')}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  viewMode === 'individual' 
                    ? 'bg-white text-gray-900 shadow-sm' 
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                Individual Files
              </button>
            </div>
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

      {viewMode === 'combined' ? (
        <div className="max-w-7xl mx-auto p-6">
          {/* Combined Type Selector */}
          {(hasIncome && hasBalance) && (
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setCombinedType('income')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  combinedType === 'income'
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                <FileText className="w-4 h-4" />
                Income Statements
              </button>
              <button
                onClick={() => setCombinedType('balance')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  combinedType === 'balance'
                    ? 'bg-green-100 text-green-700 border border-green-200'
                    : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                <Layers className="w-4 h-4" />
                Balance Sheets
              </button>
            </div>
          )}
          
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden min-h-[600px]">
            {renderCombinedView()}
          </div>
        </div>
      ) : (
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
                            ? item.docType === 'auto' 
                              ? 'Auto-Detected' 
                              : item.docType === 'income' 
                                ? 'Income Statement' 
                                : 'Balance Sheet'
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
      )}
    </div>
  );
};

export default App;
