import React, { useState, useCallback } from 'react';
import { Upload, FileText, FileSpreadsheet, Loader2, X, Plus, ChevronDown, ChevronUp, Cpu } from 'lucide-react';
import clsx from 'clsx';
import { DocType, FileUploadItem } from '../types';
import { getAllModels, getDefaultModel, getGroupedModels, getModelDisplayInfo } from '../modelConfig';

// Get models from centralized config
const AVAILABLE_MODELS = getAllModels();
const DEFAULT_MODEL = getDefaultModel();

export interface UploadOptions {
  modelOverride?: string;
  extendedThinking?: boolean;
}

interface UploadPageProps {
  onUpload: (files: FileUploadItem[], options?: UploadOptions) => void;
  isProcessing: boolean;
  processingFiles?: FileUploadItem[];
}

const generateId = () => Math.random().toString(36).substring(2, 11);

export const UploadPage: React.FC<UploadPageProps> = ({ 
  onUpload, 
  isProcessing,
  processingFiles = []
}) => {
  const [files, setFiles] = useState<FileUploadItem[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedModel, setSelectedModel] = useState(DEFAULT_MODEL.id);
  const [extendedThinking, setExtendedThinking] = useState(false);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    // Accept PDF and Excel files
    const validExtensions = ['.pdf', '.xlsx', '.xls', '.xlsm'];
    const validFiles = fileArray.filter(f => 
      f.type === 'application/pdf' || 
      f.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
      f.type === 'application/vnd.ms-excel' ||
      validExtensions.some(ext => f.name.toLowerCase().endsWith(ext))
    );
    
    const newItems: FileUploadItem[] = validFiles.map(file => ({
      id: generateId(),
      file,
      docType: guessDocType(file.name),
      status: 'pending',
      progress: 0,
    }));

    setFiles(prev => [...prev, ...newItems]);
  }, []);

  const guessDocType = (filename: string): DocType => {
    const lower = filename.toLowerCase();
    // Check if filename clearly indicates a specific type
    if (lower.includes('balance') || lower.includes('bs') || lower.includes('position')) {
      return 'balance';
    }
    if (lower.includes('income') || lower.includes('p&l') || lower.includes('profit') || lower.includes('loss')) {
      return 'income';
    }
    // Default to 'auto' for auto-detection of statement types
    return 'auto';
  };

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(e.target.files);
    }
    // Reset input value to allow selecting same file again
    e.target.value = '';
  }, [addFiles]);

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const updateDocType = (id: string, docType: DocType) => {
    setFiles(prev => prev.map(f => f.id === id ? { ...f, docType } : f));
  };

  const handleSubmit = () => {
    if (files.length > 0) {
      const options: UploadOptions = {};
      // Only pass model if it's not the default
      if (selectedModel !== DEFAULT_MODEL.id) {
        options.modelOverride = selectedModel;
      }
      // Pass extended thinking setting
      options.extendedThinking = extendedThinking;
      onUpload(files, options);
    }
  };

  const clearAll = () => {
    setFiles([]);
  };

  const displayFiles = isProcessing ? processingFiles : files;
  const hasFiles = displayFiles.length > 0;

  return (
    <div className="min-h-[calc(100vh-80px)] flex items-center justify-center p-8">
      <div className="max-w-3xl w-full space-y-6">
        {/* Header */}
        <div className="text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            Upload Financial Statements
          </h2>
          <p className="text-gray-600">
            Upload one or more PDFs to extract and spread financial data
          </p>
        </div>

        {/* Drop Zone */}
        <div
          className={clsx(
            'border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200',
            isDragging
              ? 'border-emerald-500 bg-emerald-50 scale-[1.02]'
              : 'border-gray-300 hover:border-gray-400',
            hasFiles && 'bg-gray-50/50'
          )}
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
        >
          {!hasFiles ? (
            <div className="space-y-4">
              <div className="w-16 h-16 mx-auto bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-500/20">
                <Upload className="w-8 h-8 text-white" />
              </div>
              <div>
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer text-emerald-600 hover:text-emerald-700 font-semibold text-lg"
                >
                  Choose files
                </label>
                <span className="text-gray-600 text-lg"> or drag and drop</span>
                <input
                  id="file-upload"
                  type="file"
                  accept=".pdf,.xlsx,.xls,.xlsm"
                  multiple
                  className="hidden"
                  onChange={handleFileInput}
                  disabled={isProcessing}
                />
              </div>
              <p className="text-sm text-gray-500">PDF or Excel files up to 50MB each</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* File List */}
              <div className="space-y-3 max-h-[300px] overflow-y-auto px-2">
                {displayFiles.map((item, index) => (
                  <FileRow
                    key={item.id}
                    item={item}
                    index={index}
                    onRemove={removeFile}
                    onUpdateDocType={updateDocType}
                    disabled={isProcessing}
                  />
                ))}
              </div>

              {/* Add More Button */}
              {!isProcessing && (
                <div className="flex items-center justify-center gap-4 pt-2">
                  <label
                    htmlFor="file-upload-more"
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-emerald-700 bg-emerald-50 rounded-lg hover:bg-emerald-100 cursor-pointer transition-colors"
                  >
                    <Plus className="w-4 h-4" />
                    Add more files
                    <input
                      id="file-upload-more"
                      type="file"
                      accept=".pdf,.xlsx,.xls,.xlsm"
                      multiple
                      className="hidden"
                      onChange={handleFileInput}
                    />
                  </label>
                  {files.length > 1 && (
                    <button
                      onClick={clearAll}
                      className="text-sm text-gray-500 hover:text-gray-700"
                    >
                      Clear all
                    </button>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Advanced Options */}
        {hasFiles && !isProcessing && (
          <div className="border border-gray-200 rounded-xl overflow-hidden">
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="w-full px-4 py-3 flex items-center justify-between text-sm font-medium text-gray-700 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <span className="flex items-center gap-2">
                Advanced Options
                {selectedModel !== DEFAULT_MODEL.id && (
                  <span className="text-xs px-2 py-0.5 bg-violet-100 text-violet-700 rounded-full">
                    Custom Model
                  </span>
                )}
              </span>
              {showAdvanced ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
            {showAdvanced && (
              <div className="p-4 bg-white border-t border-gray-200 space-y-4">
                {/* Model Selection */}
                <div>
                  <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
                    <Cpu className="w-4 h-4 text-gray-500" />
                    AI Model
                  </label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500"
                  >
                    {getGroupedModels().map(group => (
                      <optgroup key={group.provider} label={group.providerName}>
                        {group.models.map((model) => {
                          const displayInfo = getModelDisplayInfo(model.id);
                          return (
                            <option key={model.id} value={model.id}>
                              {displayInfo.name} - {displayInfo.description}
                            </option>
                          );
                        })}
                      </optgroup>
                    ))}
                  </select>
                </div>

                {/* Extended Thinking Toggle */}
                <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
                  <label className="flex items-center justify-between cursor-pointer">
                    <div className="flex items-center gap-3">
                      <div className="flex-shrink-0">
                        <div className={`w-12 h-6 rounded-full transition-colors ${
                          extendedThinking ? 'bg-purple-600' : 'bg-gray-300'
                        }`}>
                          <div className={`w-5 h-5 bg-white rounded-full shadow-sm transition-transform transform ${
                            extendedThinking ? 'translate-x-6' : 'translate-x-0.5'
                          } mt-0.5`} />
                        </div>
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">Extended Thinking</div>
                        <div className="text-sm text-gray-600">
                          Enable deeper reasoning for complex documents (uses more tokens)
                        </div>
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={extendedThinking}
                      onChange={(e) => setExtendedThinking(e.target.checked)}
                      className="sr-only"
                    />
                  </label>
                </div>
                
                {/* Info Text */}
                <p className="text-sm text-gray-500">
                  Document types are auto-detected from filenames. Edit them above if needed.
                  Fiscal periods are automatically detected from statement headers.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Summary Stats */}
        {hasFiles && (
          <div className="flex items-center justify-center gap-6 text-sm flex-wrap">
            {/* File type breakdown */}
            {(() => {
              const excelCount = displayFiles.filter(f => f.file.name.toLowerCase().match(/\.(xlsx|xls|xlsm)$/)).length;
              const pdfCount = displayFiles.length - excelCount;
              return (
                <>
                  {pdfCount > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-red-400"></span>
                      <span className="text-gray-600">{pdfCount} PDF</span>
                    </div>
                  )}
                  {excelCount > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="w-3 h-3 rounded-full bg-green-500"></span>
                      <span className="text-gray-600">{excelCount} Excel</span>
                    </div>
                  )}
                </>
              );
            })()}
            <span className="text-gray-300">|</span>
            {/* Doc type breakdown */}
            {displayFiles.filter(f => f.docType === 'auto').length > 0 && (
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-emerald-500"></span>
                <span className="text-gray-600">
                  {displayFiles.filter(f => f.docType === 'auto').length} Auto-Detect
                </span>
              </div>
            )}
            {displayFiles.filter(f => f.docType === 'income').length > 0 && (
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                <span className="text-gray-600">
                  {displayFiles.filter(f => f.docType === 'income').length} Income Statement(s)
                </span>
              </div>
            )}
            {displayFiles.filter(f => f.docType === 'balance').length > 0 && (
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-purple-500"></span>
                <span className="text-gray-600">
                  {displayFiles.filter(f => f.docType === 'balance').length} Balance Sheet(s)
                </span>
              </div>
            )}
          </div>
        )}

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={!hasFiles || isProcessing}
          className={clsx(
            'w-full py-4 px-6 rounded-xl font-semibold text-white transition-all duration-200 flex items-center justify-center gap-3',
            hasFiles && !isProcessing
              ? 'bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 shadow-lg shadow-emerald-500/25 hover:shadow-xl hover:shadow-emerald-500/30'
              : 'bg-gray-300 cursor-not-allowed'
          )}
        >
          {isProcessing ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Processing {displayFiles.filter(f => f.status === 'processing').length > 0 
                ? `(${displayFiles.filter(f => f.status === 'success').length}/${displayFiles.length})` 
                : '...'}
            </>
          ) : (
            <>
              <Upload className="w-5 h-5" />
              Process {files.length} Statement{files.length !== 1 ? 's' : ''}
            </>
          )}
        </button>
      </div>
    </div>
  );
};

// =============================================================================
// FILE ROW COMPONENT
// =============================================================================

interface FileRowProps {
  item: FileUploadItem;
  index: number;
  onRemove: (id: string) => void;
  onUpdateDocType: (id: string, docType: DocType) => void;
  disabled: boolean;
}

const FileRow: React.FC<FileRowProps> = ({ item, index, onRemove, onUpdateDocType, disabled }) => {
  const statusColors = {
    pending: 'bg-gray-100 text-gray-600',
    processing: 'bg-blue-100 text-blue-700',
    success: 'bg-emerald-100 text-emerald-700',
    error: 'bg-red-100 text-red-700',
  };

  const statusText = {
    pending: 'Ready',
    processing: 'Processing...',
    success: 'Complete',
    error: 'Failed',
  };

  // Determine if file is Excel
  const isExcel = item.file.name.toLowerCase().match(/\.(xlsx|xls|xlsm)$/);
  const FileIcon = isExcel ? FileSpreadsheet : FileText;

  return (
    <div
      className={clsx(
        'flex items-center gap-4 p-4 bg-white rounded-lg border transition-all duration-200',
        item.status === 'processing' && 'border-blue-300 shadow-sm',
        item.status === 'success' && 'border-emerald-300',
        item.status === 'error' && 'border-red-300',
        item.status === 'pending' && 'border-gray-200 hover:border-gray-300'
      )}
    >
      {/* File Icon - different for Excel vs PDF */}
      <div className={clsx(
        'w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0',
        isExcel 
          ? 'bg-green-100'
          : item.docType === 'auto'
            ? 'bg-emerald-100'
            : item.docType === 'income' 
              ? 'bg-blue-100' 
              : 'bg-purple-100'
      )}>
        <FileIcon className={clsx(
          'w-5 h-5',
          isExcel
            ? 'text-green-600'
            : item.docType === 'auto'
              ? 'text-emerald-600'
              : item.docType === 'income' 
                ? 'text-blue-600' 
                : 'text-purple-600'
        )} />
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <p className="font-medium text-gray-900 truncate">{item.file.name}</p>
        <p className="text-sm text-gray-500">
          {(item.file.size / 1024 / 1024).toFixed(2)} MB
        </p>
      </div>

      {/* Doc Type Selector */}
      <select
        value={item.docType}
        onChange={(e) => onUpdateDocType(item.id, e.target.value as DocType)}
        disabled={disabled}
        className={clsx(
          'px-3 py-1.5 text-sm rounded-lg border font-medium transition-colors',
          item.docType === 'auto'
            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
            : item.docType === 'income' 
              ? 'bg-blue-50 border-blue-200 text-blue-700' 
              : 'bg-purple-50 border-purple-200 text-purple-700',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <option value="auto">Auto-Detect</option>
        <option value="income">Income Statement</option>
        <option value="balance">Balance Sheet</option>
      </select>

      {/* Status Badge */}
      <span className={clsx(
        'px-3 py-1 text-xs font-medium rounded-full whitespace-nowrap',
        statusColors[item.status]
      )}>
        {item.status === 'processing' && (
          <Loader2 className="w-3 h-3 inline-block mr-1 animate-spin" />
        )}
        {statusText[item.status]}
      </span>

      {/* Remove Button */}
      {!disabled && (
        <button
          onClick={() => onRemove(item.id)}
          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
};
