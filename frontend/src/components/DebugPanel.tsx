import React, { useState, useRef, useEffect } from 'react';
import { 
  Bug, 
  X, 
  ChevronDown, 
  ChevronUp, 
  Filter, 
  Trash2, 
  Download,
  AlertCircle,
  AlertTriangle,
  Info,
  Code,
  Clock,
  FileText,
  CheckCircle,
  XCircle,
  Loader2,
  Copy,
  Check
} from 'lucide-react';
import clsx from 'clsx';
import { LogEntry, LogLevel, ProcessingStep } from '../types';

interface DebugPanelProps {
  isOpen: boolean;
  onToggle: () => void;
  logs: LogEntry[];
  steps: ProcessingStep[];
  onClear: () => void;
}

export const DebugPanel: React.FC<DebugPanelProps> = ({
  isOpen,
  onToggle,
  logs,
  steps,
  onClear,
}) => {
  const [filter, setFilter] = useState<LogLevel | 'all'>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const filteredLogs = logs.filter(log => {
    if (filter !== 'all' && log.level !== filter) return false;
    if (searchTerm && !log.message.toLowerCase().includes(searchTerm.toLowerCase())) return false;
    return true;
  });

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const toggleLogExpanded = (id: string) => {
    setExpandedLogs(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const exportLogs = () => {
    const content = JSON.stringify({ logs, steps }, null, 2);
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `debug-logs-${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyLogs = async () => {
    const content = filteredLogs.map(l => 
      `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`
    ).join('\n');
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const errorCount = logs.filter(l => l.level === 'error').length;
  const warningCount = logs.filter(l => l.level === 'warning').length;

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className={clsx(
          'fixed bottom-6 right-6 p-3 rounded-xl shadow-lg transition-all duration-200 z-50',
          'bg-gradient-to-br from-slate-800 to-slate-900 text-white',
          'hover:shadow-xl hover:scale-105',
          errorCount > 0 && 'ring-2 ring-red-500 ring-offset-2'
        )}
      >
        <div className="flex items-center gap-2">
          <Bug className="w-5 h-5" />
          {(errorCount > 0 || warningCount > 0) && (
            <div className="flex items-center gap-1">
              {errorCount > 0 && (
                <span className="px-1.5 py-0.5 text-xs font-bold bg-red-500 rounded">
                  {errorCount}
                </span>
              )}
              {warningCount > 0 && (
                <span className="px-1.5 py-0.5 text-xs font-bold bg-amber-500 rounded">
                  {warningCount}
                </span>
              )}
            </div>
          )}
        </div>
      </button>
    );
  }

  return (
    <div className="fixed bottom-0 right-0 w-full md:w-[600px] h-[500px] bg-slate-900 text-slate-100 shadow-2xl z-50 flex flex-col rounded-tl-xl overflow-hidden border-l border-t border-slate-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-800 border-b border-slate-700">
        <div className="flex items-center gap-3">
          <Bug className="w-5 h-5 text-emerald-400" />
          <span className="font-semibold">Debug Console</span>
          <div className="flex items-center gap-2 text-xs">
            {errorCount > 0 && (
              <span className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded-full font-medium">
                {errorCount} error{errorCount !== 1 ? 's' : ''}
              </span>
            )}
            {warningCount > 0 && (
              <span className="px-2 py-0.5 bg-amber-500/20 text-amber-400 rounded-full font-medium">
                {warningCount} warning{warningCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={copyLogs}
            className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
            title="Copy logs"
          >
            {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
          </button>
          <button
            onClick={exportLogs}
            className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
            title="Export logs"
          >
            <Download className="w-4 h-4" />
          </button>
          <button
            onClick={onClear}
            className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={onToggle}
            className="p-1.5 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-2 bg-slate-800/50 border-b border-slate-700/50">
        <div className="flex items-center gap-1">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as LogLevel | 'all')}
            className="bg-transparent text-sm text-slate-300 focus:outline-none cursor-pointer"
          >
            <option value="all">All Levels</option>
            <option value="debug">Debug</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="error">Error</option>
          </select>
        </div>
        <input
          type="text"
          placeholder="Search logs..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="flex-1 bg-slate-700/50 px-3 py-1.5 rounded-lg text-sm placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-emerald-500"
        />
        <label className="flex items-center gap-2 text-sm text-slate-400 cursor-pointer">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="rounded bg-slate-700 border-slate-600 text-emerald-500 focus:ring-emerald-500"
          />
          Auto-scroll
        </label>
      </div>

      {/* Processing Steps */}
      {steps.length > 0 && (
        <div className="px-4 py-3 bg-slate-800/30 border-b border-slate-700/50">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-slate-400" />
            <span className="text-sm font-medium text-slate-300">Processing Pipeline</span>
          </div>
          <div className="flex items-center gap-1">
            {steps.map((step, index) => (
              <React.Fragment key={step.id}>
                <StepBadge step={step} />
                {index < steps.length - 1 && (
                  <div className="w-4 h-0.5 bg-slate-600" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>
      )}

      {/* Log List */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto font-mono text-sm">
        {filteredLogs.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-slate-500">
            <Code className="w-8 h-8 mb-2" />
            <p>No logs to display</p>
            <p className="text-xs mt-1">Logs will appear here during processing</p>
          </div>
        ) : (
          filteredLogs.map((log) => (
            <LogRow
              key={log.id}
              log={log}
              isExpanded={expandedLogs.has(log.id)}
              onToggle={() => toggleLogExpanded(log.id)}
            />
          ))
        )}
      </div>
    </div>
  );
};

// =============================================================================
// STEP BADGE COMPONENT
// =============================================================================

const StepBadge: React.FC<{ step: ProcessingStep }> = ({ step }) => {
  const statusConfig = {
    pending: { icon: Clock, color: 'text-slate-400 bg-slate-700' },
    running: { icon: Loader2, color: 'text-blue-400 bg-blue-500/20', animate: true },
    completed: { icon: CheckCircle, color: 'text-emerald-400 bg-emerald-500/20' },
    failed: { icon: XCircle, color: 'text-red-400 bg-red-500/20' },
  };

  const config = statusConfig[step.status];
  const Icon = config.icon;

  return (
    <div
      className={clsx(
        'flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs font-medium',
        config.color
      )}
      title={step.duration ? `${step.duration}ms` : undefined}
    >
      <Icon className={clsx('w-3.5 h-3.5', config.animate && 'animate-spin')} />
      <span>{step.name}</span>
    </div>
  );
};

// =============================================================================
// LOG ROW COMPONENT
// =============================================================================

interface LogRowProps {
  log: LogEntry;
  isExpanded: boolean;
  onToggle: () => void;
}

const LogRow: React.FC<LogRowProps> = ({ log, isExpanded, onToggle }) => {
  const levelConfig = {
    debug: { icon: Code, color: 'text-slate-400', bg: 'bg-slate-500/10' },
    info: { icon: Info, color: 'text-blue-400', bg: 'bg-blue-500/10' },
    warning: { icon: AlertTriangle, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    error: { icon: AlertCircle, color: 'text-red-400', bg: 'bg-red-500/10' },
  };

  const config = levelConfig[log.level];
  const Icon = config.icon;
  const hasDetails = log.details || log.stackTrace;
  const timestamp = new Date(log.timestamp).toLocaleTimeString('en-US', { 
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3,
  });

  return (
    <div className={clsx('border-b border-slate-800 hover:bg-slate-800/30', config.bg)}>
      <div
        className={clsx(
          'flex items-start gap-3 px-4 py-2',
          hasDetails && 'cursor-pointer'
        )}
        onClick={hasDetails ? onToggle : undefined}
      >
        {/* Level Icon */}
        <Icon className={clsx('w-4 h-4 mt-0.5 flex-shrink-0', config.color)} />

        {/* Timestamp */}
        <span className="text-slate-500 text-xs font-mono w-20 flex-shrink-0 mt-0.5">
          {timestamp}
        </span>

        {/* Message */}
        <div className="flex-1 min-w-0">
          <p className={clsx('break-words', config.color)}>{log.message}</p>
          {log.filename && (
            <div className="flex items-center gap-1 mt-1 text-xs text-slate-500">
              <FileText className="w-3 h-3" />
              <span>{log.filename}</span>
            </div>
          )}
        </div>

        {/* Expand Icon */}
        {hasDetails && (
          <div className="flex-shrink-0">
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-slate-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-slate-500" />
            )}
          </div>
        )}
      </div>

      {/* Expanded Details */}
      {isExpanded && hasDetails && (
        <div className="px-4 pb-3 ml-11">
          {log.details && (
            <div className="bg-slate-800 rounded-lg p-3 text-xs overflow-x-auto">
              <pre className="text-slate-300">
                {JSON.stringify(log.details, null, 2)}
              </pre>
            </div>
          )}
          {log.stackTrace && (
            <div className="mt-2 bg-red-900/20 border border-red-500/20 rounded-lg p-3 text-xs overflow-x-auto">
              <pre className="text-red-300 whitespace-pre-wrap">{log.stackTrace}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
