import React, { useState, useEffect } from 'react';
import { PDFViewer } from './PDFViewer';
import { FinancialTable } from './FinancialTable';
import { ExportMenu } from './ExportMenu';
import { 
  SpreadMetadata, 
  FinancialStatement, 
  MultiPeriodFinancialStatement, 
  CombinedFinancialExtraction,
  isMultiPeriod,
  isCombinedExtraction 
} from '../types';
import { ArrowLeft, CheckCircle, AlertCircle, Layers, FileText, Wallet, Zap, AlertTriangle } from 'lucide-react';

interface SpreadingViewProps {
  data: FinancialStatement | MultiPeriodFinancialStatement | CombinedFinancialExtraction;
  metadata: SpreadMetadata;
  docType: 'income' | 'balance' | 'auto';
  onBack: () => void;
  hideBackButton?: boolean;
  title?: string;
}

export const SpreadingView: React.FC<SpreadingViewProps> = ({
  data,
  metadata,
  docType,
  onBack,
  hideBackButton = false,
  title,
}) => {
  // For combined view, track which tab is active
  const [activeTab, setActiveTab] = useState<'income' | 'balance'>('income');
  const [activePdfUrl, setActivePdfUrl] = useState<string | undefined>(metadata.pdf_url);
  
  // Update active PDF if metadata changes
  useEffect(() => {
    setActivePdfUrl(metadata.pdf_url);
  }, [metadata.pdf_url]);

  const isCombined = isCombinedExtraction(data);
  const combinedData = isCombined ? data as CombinedFinancialExtraction : null;
  
  // Helper to inject pdf_url into period data if not present
  const injectPdfUrlIntoPeriods = (periodData: MultiPeriodFinancialStatement | null): MultiPeriodFinancialStatement | null => {
    if (!periodData || !isMultiPeriod(periodData)) return periodData;
    
    // Only inject if periods don't already have pdf_url
    const needsInjection = periodData.periods.some(p => !p.pdf_url);
    if (!needsInjection) return periodData;
    
    return {
      ...periodData,
      periods: periodData.periods.map(p => ({
        ...p,
        pdf_url: p.pdf_url || metadata.pdf_url,
        original_filename: p.original_filename || metadata.original_filename,
      })),
    };
  };
  
  // Get the data for the current view
  const getDisplayData = () => {
    if (isCombined && combinedData) {
      if (activeTab === 'income' && combinedData.income_statement) {
        return injectPdfUrlIntoPeriods(combinedData.income_statement);
      }
      if (activeTab === 'balance' && combinedData.balance_sheet) {
        return injectPdfUrlIntoPeriods(combinedData.balance_sheet);
      }
      // Fallback to whichever is available
      return injectPdfUrlIntoPeriods(combinedData.income_statement || combinedData.balance_sheet);
    }
    
    // For non-combined data, also inject pdf_url
    const rawData = data as FinancialStatement | MultiPeriodFinancialStatement;
    if (isMultiPeriod(rawData)) {
      return injectPdfUrlIntoPeriods(rawData as MultiPeriodFinancialStatement);
    }
    return rawData;
  };
  
  const displayData = getDisplayData();
  const effectiveDocType = isCombined ? activeTab : (docType === 'auto' ? 'income' : docType);
  
  // Get the subtitle text
  const getSubtitle = () => {
    if (isCombined && combinedData) {
      const types = [];
      if (combinedData.detected_types.has_income_statement) types.push('Income Statement');
      if (combinedData.detected_types.has_balance_sheet) types.push('Balance Sheet');
      return types.join(' & ') || 'Financial Statements';
    }
    return effectiveDocType === 'income' ? 'Income Statement' : 'Balance Sheet';
  };

  const handlePeriodSelect = (pdfUrl?: string) => {
    if (pdfUrl) {
      setActivePdfUrl(pdfUrl);
    }
  };

  return (
    <div className={hideBackButton ? "flex flex-col" : "flex flex-col h-screen"}>
      {/* Fallback Prompt Warning - Fixed position at bottom */}
      {metadata.fallback_prompt_used && (
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
      
      {/* Top Bar */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 rounded-t-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {!hideBackButton && (
              <>
                <button
                  onClick={onBack}
                  className="flex items-center gap-2 text-gray-600 hover:text-gray-900 font-medium"
                >
                  <ArrowLeft className="w-5 h-5" />
                  Back
                </button>
                <div className="h-6 w-px bg-gray-300" />
              </>
            )}
            <div>
              <h2 className="text-lg font-semibold text-gray-900">
                {title || metadata.original_filename}
              </h2>
              <p className="text-sm text-gray-500">
                {getSubtitle()}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Parallel extraction indicator for combined mode */}
            {isCombined && metadata.parallel_extraction && (
              <>
                <div className="flex items-center gap-2 px-3 py-1 bg-purple-50 rounded-full">
                  <Zap className="w-4 h-4 text-purple-600" />
                  <span className="text-sm font-medium text-purple-700">
                    Parallel Extraction
                  </span>
                </div>
                <div className="h-6 w-px bg-gray-300" />
              </>
            )}
            
            {/* Multi-period indicator */}
            {displayData && isMultiPeriod(displayData) && (
              <>
                <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 rounded-full">
                  <Layers className="w-4 h-4 text-emerald-600" />
                  <span className="text-sm font-medium text-emerald-700">
                    {(displayData as MultiPeriodFinancialStatement).periods.length} Periods
                  </span>
                </div>
                <div className="h-6 w-px bg-gray-300" />
              </>
            )}
            
            {/* Extraction Stats */}
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="text-gray-700">
                  Extracted: {metadata.total_fields - metadata.missing}/{metadata.total_fields}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-confidence-high" />
                <span className="text-gray-700">{metadata.high_confidence} high</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-confidence-medium" />
                <span className="text-gray-700">{metadata.medium_confidence} medium</span>
              </div>
              {metadata.low_confidence > 0 && (
                <div className="flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-confidence-low" />
                  <span className="text-gray-700">{metadata.low_confidence} low</span>
                </div>
              )}
            </div>

            <div className="h-6 w-px bg-gray-300" />

            {displayData && (
              <ExportMenu 
                data={displayData} 
                metadata={metadata} 
                docType={effectiveDocType}
                fullData={isCombined ? combinedData || undefined : undefined}
              />
            )}
          </div>
        </div>
        
        {/* Tab selector for combined view */}
        {isCombined && combinedData && (
          <div className="flex gap-2 mt-4 pt-4 border-t border-gray-100">
            {combinedData.income_statement && (
              <button
                onClick={() => setActiveTab('income')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'income'
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <FileText className="w-4 h-4" />
                Income Statement
                {combinedData.income_statement.periods && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full bg-white/50">
                    {combinedData.income_statement.periods.length} periods
                  </span>
                )}
              </button>
            )}
            {combinedData.balance_sheet && (
              <button
                onClick={() => setActiveTab('balance')}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  activeTab === 'balance'
                    ? 'bg-green-100 text-green-700 border border-green-200'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <Wallet className="w-4 h-4" />
                Balance Sheet
                {combinedData.balance_sheet.periods && (
                  <span className="text-xs px-1.5 py-0.5 rounded-full bg-white/50">
                    {combinedData.balance_sheet.periods.length} periods
                  </span>
                )}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Main Content - Side by Side */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - PDF Viewer */}
        <div className="w-1/2 border-r border-gray-200">
          <PDFViewer pdfUrl={activePdfUrl || metadata.pdf_url} />
        </div>

        {/* Right Panel - Financial Table */}
        <div className="w-1/2 overflow-auto bg-gray-50">
          <div className="p-6">
            {displayData ? (
              <FinancialTable 
                data={displayData} 
                docType={effectiveDocType} 
                onPeriodSelect={handlePeriodSelect}
              />
            ) : (
              <div className="text-center text-gray-500 py-8">
                No data available for this statement type
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
