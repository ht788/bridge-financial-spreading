import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Copy, Check, FileJson, Download } from 'lucide-react';

interface JsonViewerProps {
  data: any;
  title: string;
  className?: string;
}

export const JsonViewer: React.FC<JsonViewerProps> = ({ data, title, className = '' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.replace(/\s+/g, '_')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className={`border border-gray-200 rounded-lg overflow-hidden bg-white ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
          <FileJson className="w-4 h-4 text-blue-500" />
          <span className="font-medium text-gray-700 text-sm">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          {isOpen && (
            <>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDownload();
                }}
                className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                title="Download JSON"
              >
                <Download className="w-3.5 h-3.5 text-gray-600" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleCopy();
                }}
                className="p-1.5 hover:bg-gray-200 rounded transition-colors"
                title="Copy to clipboard"
              >
                {copied ? (
                  <Check className="w-3.5 h-3.5 text-green-600" />
                ) : (
                  <Copy className="w-3.5 h-3.5 text-gray-600" />
                )}
              </button>
            </>
          )}
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            JSON
          </span>
        </div>
      </button>
      
      {isOpen && (
        <div className="border-t border-gray-200 bg-gray-50">
          <div className="max-h-96 overflow-auto p-4">
            <pre className="text-xs font-mono text-gray-800 whitespace-pre-wrap break-words">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

interface JsonViewerContainerProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

export const JsonViewerContainer: React.FC<JsonViewerContainerProps> = ({
  title,
  children,
  className = '',
}) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={`bg-gray-50 border border-gray-200 rounded-lg ${className}`}>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-2 flex items-center justify-between hover:bg-gray-100 transition-colors rounded-t-lg"
      >
        <div className="flex items-center gap-2">
          <FileJson className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-medium text-gray-700">{title}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">
            {isExpanded ? 'Hide' : 'Show'} JSON Data
          </span>
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-gray-500" />
          ) : (
            <ChevronRight className="w-4 h-4 text-gray-500" />
          )}
        </div>
      </button>
      
      {isExpanded && (
        <div className="border-t border-gray-200 p-4 space-y-2">
          {children}
        </div>
      )}
    </div>
  );
};
