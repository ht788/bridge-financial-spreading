import React, { useState } from 'react';
import { Download, FileJson, FileSpreadsheet } from 'lucide-react';
import { FinancialStatement, SpreadMetadata, MultiPeriodFinancialStatement, CombinedFinancialExtraction } from '../types';
import { exportToJSON, exportToCSV, exportCombinedToCSV } from '../utils';
import clsx from 'clsx';

interface ExportMenuProps {
  data: FinancialStatement | MultiPeriodFinancialStatement | CombinedFinancialExtraction;
  metadata: SpreadMetadata;
  docType: 'income' | 'balance';
  // For combined extractions, pass the full data
  fullData?: CombinedFinancialExtraction;
}

export const ExportMenu: React.FC<ExportMenuProps> = ({ data, metadata, docType, fullData }) => {
  const [isOpen, setIsOpen] = useState(false);
  
  // Determine if this is a combined extraction
  const isCombined = fullData !== undefined;

  const handleExportJSON = () => {
    let filename: string;
    let exportData: any;
    
    if (isCombined && fullData) {
      // Export the full combined extraction with both statements
      filename = `${metadata.original_filename.replace('.pdf', '')}_combined_statements.json`;
      exportData = { data: fullData, metadata };
    } else {
      // Export single statement type
      filename = `${metadata.original_filename.replace('.pdf', '')}_${docType}_statement.json`;
      exportData = { data, metadata };
    }
    
    exportToJSON(exportData, filename);
    setIsOpen(false);
  };

  const handleExportCSV = () => {
    if (isCombined && fullData) {
      // Export both statements to separate CSV files
      const baseFilename = metadata.original_filename.replace('.pdf', '');
      exportCombinedToCSV(fullData, baseFilename, metadata);
    } else {
      // Export single statement type
      const filename = `${metadata.original_filename.replace('.pdf', '')}_${docType}_statement.csv`;
      exportToCSV(data as any, filename, metadata);
    }
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
      >
        <Download className="w-4 h-4" />
        Export
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
            <div className="py-2">
              <button
                onClick={handleExportJSON}
                className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center gap-3 text-gray-700"
              >
                <FileJson className="w-4 h-4 text-blue-600" />
                <div>
                  <div className="font-medium">Export as JSON</div>
                  <div className="text-xs text-gray-500">
                    {isCombined ? 'Both statements included' : 'Structured data format'}
                  </div>
                </div>
              </button>
              <button
                onClick={handleExportCSV}
                className="w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center gap-3 text-gray-700"
              >
                <FileSpreadsheet className="w-4 h-4 text-green-600" />
                <div>
                  <div className="font-medium">Export as CSV</div>
                  <div className="text-xs text-gray-500">
                    {isCombined ? 'Creates 2 files (IS + BS)' : 'Spreadsheet compatible'}
                  </div>
                </div>
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
