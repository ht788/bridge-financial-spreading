import React, { useState } from 'react';
import { 
  CheckCircle, XCircle, AlertCircle, MinusCircle, 
  ChevronDown, FileText, Clock, Target, BarChart3,
  Maximize2, Minimize2, Eye, AlertTriangle
} from 'lucide-react';
import { PDFViewer } from '../PDFViewer';
import { API_BASE_URL } from '../../api';
import { 
  TestRunResult, 
  FileGrade, 
  PeriodGrade, 
  FieldComparison,
  getGradeColor, 
  getAccuracyColor, 
  getAccuracyLabel,
  formatScore,
  formatDuration
} from '../../testingTypes';

interface TestResultsComparisonProps {
  result: TestRunResult;
}

export const TestResultsComparison: React.FC<TestResultsComparisonProps> = ({ result }) => {
  const [selectedFileIndex, setSelectedFileIndex] = useState(0);
  const [selectedPeriodIndex, setSelectedPeriodIndex] = useState(0);
  const [expandedFields, setExpandedFields] = useState<Set<string>>(new Set());
  const [showPdf, setShowPdf] = useState(true);

  const selectedFile = result.file_results[selectedFileIndex];
  const selectedPeriod = selectedFile?.periods[selectedPeriodIndex];

  const toggleField = (fieldName: string) => {
    const newExpanded = new Set(expandedFields);
    if (newExpanded.has(fieldName)) {
      newExpanded.delete(fieldName);
    } else {
      newExpanded.add(fieldName);
    }
    setExpandedFields(newExpanded);
  };

  const pdfUrl = selectedFile ? `${API_BASE_URL}/testing/files/${selectedFile.filename}` : '';

  return (
    <div className="flex flex-col h-[calc(100vh-140px)]">
      {/* Fallback Prompt Warning - Fixed position at bottom */}
      {result.fallback_prompt_used && (
        <div className="fixed bottom-4 left-4 z-50 bg-amber-50 border border-amber-200 rounded-lg shadow-lg px-4 py-3 max-w-md">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-amber-900">Fallback Prompt Used</p>
              <p className="text-xs text-amber-700 mt-1">
                The Hub prompt system message could not be extracted. A basic fallback prompt was used instead.
              </p>
            </div>
          </div>
        </div>
      )}
      
      {/* Summary Header - Compact */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden flex-shrink-0 mb-4">
        <div className={`px-4 py-3 ${
          result.overall_grade === 'A+' || result.overall_grade === 'A' 
            ? 'bg-gradient-to-r from-emerald-500 to-green-600' 
            : result.overall_grade === 'B' 
              ? 'bg-gradient-to-r from-blue-500 to-cyan-600'
              : result.overall_grade === 'C'
                ? 'bg-gradient-to-r from-yellow-500 to-amber-600'
                : 'bg-gradient-to-r from-red-500 to-rose-600'
        } text-white`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-3">
                <span className="px-2 py-0.5 bg-white/20 rounded text-lg font-bold">
                  {result.overall_grade}
                </span>
                <span className="text-xl font-bold">{formatScore(result.overall_score)}</span>
              </div>
              <div className="h-8 w-px bg-white/20" />
              <div>
                <p className="font-medium">{result.company_name}</p>
                <p className="text-xs text-white/80">{result.model_name}</p>
              </div>
            </div>
            
            <div className="flex items-center gap-6 text-sm">
               <div className="flex items-center gap-2">
                 <span className="text-white/80">Correct:</span>
                 <span className="font-bold">{result.fields_correct}</span>
               </div>
               <div className="flex items-center gap-2">
                 <span className="text-white/80">Partial:</span>
                 <span className="font-bold">{result.fields_partial}</span>
               </div>
               <div className="flex items-center gap-2">
                 <span className="text-white/80">Wrong:</span>
                 <span className="font-bold">{result.fields_wrong}</span>
               </div>
               <div className="flex items-center gap-2">
                 <span className="text-white/80">Missing:</span>
                 <span className="font-bold">{result.fields_missing}</span>
               </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area - Split View */}
      <div className="flex-1 flex overflow-hidden gap-4 min-h-0">
        {/* Left Pane: PDF Viewer */}
        {showPdf && selectedFile && (
           <div className="flex-1 bg-white border border-gray-200 rounded-xl overflow-hidden flex flex-col shadow-sm">
              <div className="px-3 py-2 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                 <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-gray-500" />
                    <span className="font-medium text-sm text-gray-700 truncate max-w-[300px]" title={selectedFile.filename}>
                      {selectedFile.filename}
                    </span>
                 </div>
                 <button 
                   onClick={() => setShowPdf(false)}
                   className="p-1 hover:bg-gray-200 rounded text-gray-500 transition-colors"
                   title="Hide PDF"
                 >
                   <Minimize2 className="w-4 h-4" />
                 </button>
              </div>
              <div className="flex-1 overflow-hidden relative">
                 <PDFViewer pdfUrl={pdfUrl} />
              </div>
           </div>
        )}

        {/* Right Pane: Results */}
        <div className={`${showPdf ? 'w-[500px] xl:w-[600px]' : 'w-full'} flex flex-col gap-4 transition-all duration-300 flex-shrink-0`}>
           
           {/* Controls if PDF is hidden */}
           {!showPdf && (
             <div className="flex justify-end">
               <button 
                 onClick={() => setShowPdf(true)}
                 className="flex items-center gap-2 text-sm text-violet-600 font-medium hover:text-violet-700"
               >
                 <Maximize2 className="w-4 h-4" />
                 Show PDF
               </button>
             </div>
           )}

           {/* File List */}
           <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm flex-shrink-0 max-h-[200px] flex flex-col">
             <div className="px-4 py-2 bg-gray-50 border-b border-gray-200">
               <h4 className="font-medium text-gray-900 text-sm">Test Files</h4>
             </div>
             <div className="divide-y divide-gray-100 overflow-y-auto">
               {result.file_results.map((file, idx) => (
                 <button
                   key={idx}
                   onClick={() => {
                     setSelectedFileIndex(idx);
                     setSelectedPeriodIndex(0);
                   }}
                   className={`w-full px-4 py-2 text-left transition-colors ${
                     idx === selectedFileIndex
                       ? 'bg-violet-50 border-l-2 border-violet-500'
                       : 'hover:bg-gray-50 border-l-2 border-transparent'
                   }`}
                 >
                   <div className="flex items-center justify-between">
                     <div className="flex items-center gap-2 min-w-0 flex-1">
                       <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium flex-shrink-0 ${
                         file.doc_type === 'income' 
                           ? 'bg-blue-100 text-blue-700' 
                           : 'bg-emerald-100 text-emerald-700'
                       }`}>
                         {file.doc_type === 'income' ? 'P&L' : 'BS'}
                       </span>
                       <span className="text-sm font-medium text-gray-900 truncate pr-2">
                         {file.filename}
                       </span>
                     </div>
                     <div className="flex items-center gap-2 flex-shrink-0">
                       <span className={`text-xs px-1.5 py-0.5 rounded border ${getGradeColor(file.overall_grade)}`}>
                         {file.overall_grade}
                       </span>
                       <span className="text-xs text-gray-500 w-10 text-right">
                         {formatScore(file.overall_score)}
                       </span>
                     </div>
                   </div>
                 </button>
               ))}
             </div>
           </div>

           {/* Results Detail */}
           <div className="flex-1 bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm flex flex-col min-h-0">
              {selectedFile ? (
                <>
                  {/* Period Tabs */}
                  {selectedFile.periods.length > 0 && (
                    <div className="flex border-b border-gray-200 bg-gray-50 overflow-x-auto">
                      {selectedFile.periods.map((period, idx) => (
                        <button
                          key={idx}
                          onClick={() => setSelectedPeriodIndex(idx)}
                          className={`px-4 py-2 text-sm font-medium transition-colors whitespace-nowrap ${
                            idx === selectedPeriodIndex
                              ? 'text-violet-600 border-b-2 border-violet-500 bg-white'
                              : 'text-gray-600 hover:text-gray-900'
                          }`}
                        >
                          {period.period_label}
                          <span className={`ml-2 text-xs px-1.5 py-0.5 rounded ${getGradeColor(period.grade)}`}>
                            {period.grade}
                          </span>
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Period Details */}
                  {selectedPeriod ? (
                    <div className="flex-1 flex flex-col min-h-0">
                      {/* Period Summary */}
                      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 flex-shrink-0">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className={`text-lg font-bold px-2 py-1 rounded border ${getGradeColor(selectedPeriod.grade)}`}>
                              {selectedPeriod.grade}
                            </span>
                            <span className="text-lg font-semibold text-gray-900">
                              {formatScore(selectedPeriod.score)}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-gray-600">
                            <span className="flex items-center gap-1" title="Exact Match">
                              <CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                              {selectedPeriod.matched_fields}
                            </span>
                            <span className="flex items-center gap-1" title="Partial Match">
                              <AlertCircle className="w-3.5 h-3.5 text-yellow-500" />
                              {selectedPeriod.partial_fields}
                            </span>
                            <span className="flex items-center gap-1" title="Wrong/Missing">
                              <XCircle className="w-3.5 h-3.5 text-red-500" />
                              {selectedPeriod.wrong_fields + selectedPeriod.missing_fields}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Field Comparisons */}
                      <div className="flex-1 overflow-y-auto divide-y divide-gray-100">
                        {selectedPeriod.field_comparisons.map((comparison, idx) => (
                          <FieldComparisonRow 
                            key={idx} 
                            comparison={comparison}
                            isExpanded={expandedFields.has(comparison.field_name)}
                            onToggle={() => toggleField(comparison.field_name)}
                          />
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="flex-1 flex items-center justify-center text-gray-500">
                      No period data available
                    </div>
                  )}
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                  Select a file to view results
                </div>
              )}
           </div>
        </div>
      </div>
    </div>
  );
};

interface FieldComparisonRowProps {
  comparison: FieldComparison;
  isExpanded: boolean;
  onToggle: () => void;
}

const FieldComparisonRow: React.FC<FieldComparisonRowProps> = ({ 
  comparison, 
  isExpanded, 
  onToggle 
}) => {
  const formatValue = (value: number | null): string => {
    if (value === null) return '—';
    return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const getStatusIcon = () => {
    switch (comparison.accuracy) {
      case 'exact':
        return <CheckCircle className="w-4 h-4 text-emerald-500" />;
      case 'tolerance':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'partial':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      case 'missing':
        return <MinusCircle className="w-4 h-4 text-gray-400" />;
      case 'wrong':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'extra':
        return <AlertCircle className="w-4 h-4 text-blue-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="hover:bg-gray-50 transition-colors">
      <button
        onClick={onToggle}
        className="w-full px-4 py-2.5 flex items-center gap-3 text-left group"
      >
        <div className="mt-0.5">{getStatusIcon()}</div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-0.5">
            <div className="font-medium text-gray-900 text-sm truncate pr-2" title={comparison.field_name}>
              {comparison.field_name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </div>
            <span className={`text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold ${getAccuracyColor(comparison.accuracy)}`}>
              {getAccuracyLabel(comparison.accuracy)}
            </span>
          </div>
          
          <div className="flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Exp:</span>
              <span className="text-gray-900">{formatValue(comparison.expected_value)}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-500">Got:</span>
              <span className={comparison.accuracy === 'exact' || comparison.accuracy === 'tolerance' 
                ? 'text-emerald-600 font-medium' 
                : comparison.accuracy === 'partial' 
                  ? 'text-yellow-600 font-medium' 
                  : 'text-red-600 font-medium'
              }>
                {formatValue(comparison.extracted_value)}
              </span>
            </div>
          </div>
        </div>

        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform group-hover:text-gray-600 ${isExpanded ? 'rotate-180' : ''}`} />
      </button>

      {isExpanded && (
        <div className="px-4 pb-3 pl-11">
          <div className="bg-gray-50 rounded p-2 text-xs border border-gray-100">
            {comparison.difference_percent !== undefined && comparison.difference_percent !== null && (
              <div className="flex justify-between text-gray-600 mb-1">
                <span>Difference:</span>
                <span className="font-mono">
                  {comparison.difference?.toLocaleString()} ({comparison.difference_percent.toFixed(2)}%)
                </span>
              </div>
            )}
            <div className="flex justify-between text-gray-600 mb-1">
              <span>Tolerance:</span>
              <span className="font-mono">{comparison.tolerance_used}%</span>
            </div>
            {comparison.notes && (
              <div className="text-gray-500 mt-2 border-t border-gray-200 pt-1 italic">
                {comparison.notes}
              </div>
            )}
            <div className="flex justify-between text-gray-600 mt-2 pt-2 border-t border-gray-200">
              <span>Score:</span>
              <span className="font-bold text-gray-900">{(comparison.score * 100).toFixed(0)}%</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};