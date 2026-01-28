import React from 'react';
import { PDFViewer } from './PDFViewer';
import { FinancialTable } from './FinancialTable';
import { ExportMenu } from './ExportMenu';
import { SpreadMetadata, FinancialStatement, MultiPeriodFinancialStatement, isMultiPeriod } from '../types';
import { ArrowLeft, CheckCircle, AlertCircle, Layers } from 'lucide-react';

interface SpreadingViewProps {
  data: FinancialStatement | MultiPeriodFinancialStatement;
  metadata: SpreadMetadata;
  docType: 'income' | 'balance';
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
  return (
    <div className={hideBackButton ? "flex flex-col" : "flex flex-col h-screen"}>
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
                {docType === 'income' ? 'Income Statement' : 'Balance Sheet'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Multi-period indicator */}
            {isMultiPeriod(data) && (
              <>
                <div className="flex items-center gap-2 px-3 py-1 bg-emerald-50 rounded-full">
                  <Layers className="w-4 h-4 text-emerald-600" />
                  <span className="text-sm font-medium text-emerald-700">
                    {(data as MultiPeriodFinancialStatement).periods.length} Periods
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

            <ExportMenu data={data} metadata={metadata} docType={docType} />
          </div>
        </div>
      </div>

      {/* Main Content - Side by Side */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - PDF Viewer */}
        <div className="w-1/2 border-r border-gray-200">
          <PDFViewer pdfUrl={metadata.pdf_url} />
        </div>

        {/* Right Panel - Financial Table */}
        <div className="w-1/2 overflow-auto bg-gray-50">
          <div className="p-6">
            <FinancialTable data={data} docType={docType} />
          </div>
        </div>
      </div>
    </div>
  );
};
