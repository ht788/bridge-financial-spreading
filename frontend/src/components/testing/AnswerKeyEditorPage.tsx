import React, { useState, useEffect, useCallback, useRef } from 'react';
import { 
  ArrowLeft, 
  Save, 
  FileText, 
  FileSpreadsheet, 
  Check, 
  AlertCircle,
  ChevronRight,
  ChevronDown,
  Edit3,
  RefreshCw,
  Loader2,
  CheckCircle,
  X
} from 'lucide-react';
import { testingApi } from '../../testingApi';
import { 
  TestCompany, 
  CompanyAnswerKey,
  ExpectedLineItem,
  PeriodStatements,
  StatementAnswerKey
} from '../../testingTypes';
import { PDFViewer } from '../PDFViewer';

interface AnswerKeyEditorPageProps {
  onBack: () => void;
}

// Field name display mapping
const FIELD_DISPLAY_NAMES: Record<string, string> = {
  // Income Statement
  revenue: 'Revenue',
  cogs: 'Cost of Goods Sold',
  gross_profit: 'Gross Profit',
  sga: 'SG&A',
  research_and_development: 'R&D',
  depreciation_amortization: 'Depreciation & Amortization',
  other_operating_expenses: 'Other Operating Expenses',
  total_operating_expenses: 'Total Operating Expenses',
  operating_income: 'Operating Income',
  interest_expense: 'Interest Expense',
  interest_income: 'Interest Income',
  other_income_expense: 'Other Income/Expense',
  pretax_income: 'Pre-tax Income',
  income_tax_expense: 'Income Tax Expense',
  net_income: 'Net Income',
  
  // Balance Sheet
  cash_and_equivalents: 'Cash & Equivalents',
  accounts_receivable: 'Accounts Receivable',
  inventory: 'Inventory',
  prepaid_and_other_current: 'Prepaid & Other Current',
  total_current_assets: 'Total Current Assets',
  net_ppe: 'Net PP&E',
  goodwill_and_intangibles: 'Goodwill & Intangibles',
  other_noncurrent_assets: 'Other Non-Current Assets',
  total_assets: 'Total Assets',
  accounts_payable: 'Accounts Payable',
  current_portion_ltd: 'Current Portion LTD',
  other_current_liabilities: 'Other Current Liabilities',
  total_current_liabilities: 'Total Current Liabilities',
  long_term_debt: 'Long-Term Debt',
  other_noncurrent_liabilities: 'Other Non-Current Liabilities',
  total_liabilities: 'Total Liabilities',
  total_shareholders_equity: 'Total Shareholders\' Equity',
  total_liabilities_and_equity: 'Total Liabilities & Equity',
};

export const AnswerKeyEditorPage: React.FC<AnswerKeyEditorPageProps> = ({ onBack }) => {
  // State
  const [companies, setCompanies] = useState<TestCompany[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [answerKey, setAnswerKey] = useState<CompanyAnswerKey | null>(null);
  const [selectedPeriodIndex, setSelectedPeriodIndex] = useState<number>(0);
  const [selectedStatementType, setSelectedStatementType] = useState<'income' | 'balance'>('income');
  const [expandedPeriods, setExpandedPeriods] = useState<Set<number>>(new Set([0]));
  const [status, setStatus] = useState<'loading' | 'idle' | 'saving' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  
  // Refs
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load companies on mount
  useEffect(() => {
    loadCompanies();
  }, []);

  const loadCompanies = async () => {
    try {
      setStatus('loading');
      const response = await testingApi.getStatus();
      setCompanies(response.available_companies);
      
      // Auto-select first company
      if (response.available_companies.length > 0) {
        setSelectedCompanyId(response.available_companies[0].id);
      }
      setStatus('idle');
    } catch (err: any) {
      setError(err.message || 'Failed to load companies');
      setStatus('error');
    }
  };

  // Load answer key when company changes
  useEffect(() => {
    if (selectedCompanyId) {
      loadAnswerKey(selectedCompanyId);
    }
  }, [selectedCompanyId]);

  const loadAnswerKey = async (companyId: string) => {
    try {
      setStatus('loading');
      setError(null);
      const key = await testingApi.getAnswerKey(companyId);
      setAnswerKey(key);
      setSelectedPeriodIndex(0);
      setSelectedStatementType('income');
      setExpandedPeriods(new Set([0]));
      setHasUnsavedChanges(false);
      setStatus('idle');
    } catch (err: any) {
      setError(err.message || 'Failed to load answer key');
      setStatus('error');
    }
  };

  // Auto-save with debounce
  const saveAnswerKey = useCallback(async (keyToSave: CompanyAnswerKey) => {
    try {
      setSaveStatus('saving');
      await testingApi.updateAnswerKey(keyToSave);
      setSaveStatus('saved');
      setHasUnsavedChanges(false);
      
      // Reset save status after a delay
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch (err: any) {
      setSaveStatus('error');
      setError(err.message || 'Failed to save answer key');
    }
  }, []);

  const handleFieldChange = useCallback((
    periodIdx: number,
    statementType: 'income' | 'balance',
    fieldName: string,
    property: keyof ExpectedLineItem,
    value: any
  ) => {
    if (!answerKey) return;

    const newAnswerKey = { ...answerKey };
    const periods = [...newAnswerKey.periods];
    const period = { ...periods[periodIdx] };
    
    // Get or create the statement
    let statement = statementType === 'income' ? period.income : period.balance;
    if (!statement) {
      statement = { expected: {} };
    } else {
      statement = { ...statement, expected: { ...statement.expected } };
    }
    
    const field = { ...(statement.expected[fieldName] || { value: null, tolerance_percent: 5.0, required: false }) };

    // Handle value conversion
    if (property === 'value') {
      field.value = value === '' || value === null ? null : parseFloat(value);
    } else if (property === 'tolerance_percent') {
      field.tolerance_percent = parseFloat(value) || 5.0;
    } else if (property === 'required') {
      field.required = value;
    } else if (property === 'notes') {
      field.notes = value;
    }

    statement.expected[fieldName] = field;
    
    if (statementType === 'income') {
      period.income = statement;
    } else {
      period.balance = statement;
    }
    
    periods[periodIdx] = period;
    newAnswerKey.periods = periods;

    setAnswerKey(newAnswerKey);
    setHasUnsavedChanges(true);

    // Debounced auto-save
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(() => {
      saveAnswerKey(newAnswerKey);
    }, 1500);
  }, [answerKey, saveAnswerKey]);

  const handleManualSave = async () => {
    if (answerKey) {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
      await saveAnswerKey(answerKey);
    }
  };

  const togglePeriodExpanded = (periodIdx: number) => {
    setExpandedPeriods(prev => {
      const next = new Set(prev);
      if (next.has(periodIdx)) {
        next.delete(periodIdx);
      } else {
        next.add(periodIdx);
      }
      return next;
    });
  };

  const selectPeriodStatement = (periodIdx: number, statementType: 'income' | 'balance') => {
    setSelectedPeriodIndex(periodIdx);
    setSelectedStatementType(statementType);
    setExpandedPeriods(prev => new Set(prev).add(periodIdx));
  };

  const selectedPeriod = answerKey?.periods[selectedPeriodIndex];
  const selectedStatement = selectedPeriod 
    ? (selectedStatementType === 'income' ? selectedPeriod.income : selectedPeriod.balance)
    : null;

  // Get company files for the selected period/statement (for PDF viewer reference)
  const selectedCompany = companies.find(c => c.id === selectedCompanyId);
  const relevantFiles = selectedCompany?.files.filter(f => 
    f.doc_type === selectedStatementType || f.doc_type === 'auto'
  ) || [];

  // Get file URL for viewer - use the first relevant file for reference
  const getFileUrl = () => {
    if (relevantFiles.length === 0) return '';
    return testingApi.getTestFileUrl(relevantFiles[0].filename);
  };

  const firstRelevantFile = relevantFiles[0];
  const isExcelFile = firstRelevantFile?.filename.toLowerCase().endsWith('.xlsx') || 
                      firstRelevantFile?.filename.toLowerCase().endsWith('.xls');

  return (
    <div className="min-h-[calc(100vh-80px)] bg-gradient-to-br from-violet-50/50 via-white to-purple-50/50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 sticky top-[73px] z-30">
        <div className="max-w-[98%] mx-auto px-4 py-4">
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
                <div className="bg-gradient-to-br from-amber-500 to-orange-600 p-2 rounded-lg">
                  <Edit3 className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Answer Key Editor</h2>
                  <p className="text-xs text-gray-500">Edit expected values for test evaluation</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Save Status */}
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm ${
                saveStatus === 'saving'
                  ? 'bg-blue-50 text-blue-700'
                  : saveStatus === 'saved'
                    ? 'bg-green-50 text-green-700'
                    : saveStatus === 'error'
                      ? 'bg-red-50 text-red-700'
                      : hasUnsavedChanges
                        ? 'bg-yellow-50 text-yellow-700'
                        : 'bg-gray-50 text-gray-500'
              }`}>
                {saveStatus === 'saving' ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : saveStatus === 'saved' ? (
                  <>
                    <CheckCircle className="w-4 h-4" />
                    <span>Saved</span>
                  </>
                ) : saveStatus === 'error' ? (
                  <>
                    <AlertCircle className="w-4 h-4" />
                    <span>Save failed</span>
                  </>
                ) : hasUnsavedChanges ? (
                  <>
                    <div className="w-2 h-2 bg-yellow-500 rounded-full" />
                    <span>Unsaved changes</span>
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4" />
                    <span>All changes saved</span>
                  </>
                )}
              </div>

              {/* Manual Save Button */}
              <button
                onClick={handleManualSave}
                disabled={!hasUnsavedChanges || saveStatus === 'saving'}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                  hasUnsavedChanges && saveStatus !== 'saving'
                    ? 'bg-violet-600 text-white hover:bg-violet-700'
                    : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                }`}
              >
                <Save className="w-4 h-4" />
                Save
              </button>

              {/* Reload Button */}
              <button
                onClick={() => selectedCompanyId && loadAnswerKey(selectedCompanyId)}
                disabled={status === 'loading'}
                className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                title="Reload from file"
              >
                <RefreshCw className={`w-4 h-4 ${status === 'loading' ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-[98%] mx-auto px-4 py-4">
        {status === 'loading' && !answerKey && (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="w-12 h-12 border-3 border-violet-500/30 border-t-violet-500 rounded-full animate-spin mx-auto" />
              <p className="text-gray-600 mt-4">Loading answer keys...</p>
            </div>
          </div>
        )}

        {status === 'error' && !answerKey && (
          <div className="max-w-lg mx-auto py-20">
            <div className="bg-white border border-red-200 rounded-2xl p-8 text-center">
              <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <AlertCircle className="w-8 h-8 text-red-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Error</h3>
              <p className="text-gray-600 mb-6">{error}</p>
              <button
                onClick={loadCompanies}
                className="px-6 py-2.5 bg-violet-600 text-white rounded-xl hover:bg-violet-700 transition-colors font-medium"
              >
                Retry
              </button>
            </div>
          </div>
        )}

        {answerKey && (
          <div className="grid grid-cols-12 gap-4 h-[calc(100vh-200px)]">
            {/* Left Sidebar - File Navigator */}
            <div className="col-span-2 bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
              {/* Company Selector */}
              <div className="p-3 border-b border-gray-200 bg-gray-50">
                <select
                  value={selectedCompanyId || ''}
                  onChange={(e) => setSelectedCompanyId(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-violet-500 focus:border-violet-500"
                >
                  {companies.map(c => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              {/* Period Tree */}
              <div className="flex-1 overflow-y-auto p-2">
                <div className="space-y-1">
                  {answerKey.periods.map((period, periodIdx) => (
                    <div key={period.period_label}>
                      {/* Period Header */}
                      <button
                        onClick={() => togglePeriodExpanded(periodIdx)}
                        className={`w-full flex items-center gap-2 px-2 py-2 rounded-lg text-left text-sm transition-colors ${
                          selectedPeriodIndex === periodIdx
                            ? 'bg-violet-50 text-violet-700'
                            : 'hover:bg-gray-100 text-gray-700'
                        }`}
                      >
                        {expandedPeriods.has(periodIdx) ? (
                          <ChevronDown className="w-4 h-4 flex-shrink-0" />
                        ) : (
                          <ChevronRight className="w-4 h-4 flex-shrink-0" />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="truncate text-xs font-medium">
                            {period.period_label}
                          </div>
                          <div className="text-[10px] text-gray-400">
                            {[period.income && 'IS', period.balance && 'BS'].filter(Boolean).join(' + ') || 'No data'}
                          </div>
                        </div>
                      </button>

                      {/* Statement Types */}
                      {expandedPeriods.has(periodIdx) && (
                        <div className="ml-6 mt-1 space-y-0.5">
                          {period.income && (
                            <button
                              onClick={() => selectPeriodStatement(periodIdx, 'income')}
                              className={`w-full px-3 py-1.5 text-xs text-left rounded transition-colors flex items-center gap-2 ${
                                selectedPeriodIndex === periodIdx && selectedStatementType === 'income'
                                  ? 'bg-violet-100 text-violet-800 font-medium'
                                  : 'text-gray-600 hover:bg-gray-100'
                              }`}
                            >
                              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                              Income Statement
                            </button>
                          )}
                          {period.balance && (
                            <button
                              onClick={() => selectPeriodStatement(periodIdx, 'balance')}
                              className={`w-full px-3 py-1.5 text-xs text-left rounded transition-colors flex items-center gap-2 ${
                                selectedPeriodIndex === periodIdx && selectedStatementType === 'balance'
                                  ? 'bg-violet-100 text-violet-800 font-medium'
                                  : 'text-gray-600 hover:bg-gray-100'
                              }`}
                            >
                              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                              Balance Sheet
                            </button>
                          )}
                          {!period.income && !period.balance && (
                            <div className="px-3 py-1.5 text-xs text-gray-400 italic">
                              No statements defined
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Middle - File Viewer */}
            <div className="col-span-5 bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {isExcelFile ? (
                    <FileSpreadsheet className="w-4 h-4 text-green-600" />
                  ) : (
                    <FileText className="w-4 h-4 text-red-600" />
                  )}
                  <span className="font-medium text-sm text-gray-700 truncate max-w-[300px]">
                    {firstRelevantFile?.filename.split('/').pop() || 'No source file'}
                  </span>
                </div>
                {firstRelevantFile && (
                  <a
                    href={getFileUrl()}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-violet-600 hover:text-violet-800 hover:underline"
                  >
                    Open in new tab
                  </a>
                )}
              </div>
              <div className="flex-1 bg-gray-100 overflow-hidden">
                {firstRelevantFile ? (
                  isExcelFile ? (
                    <div className="h-full flex items-center justify-center text-gray-500">
                      <div className="text-center p-6">
                        <FileSpreadsheet className="w-16 h-16 mx-auto text-green-400 mb-4" />
                        <p className="text-sm font-medium mb-2">Excel File</p>
                        <p className="text-xs text-gray-400 mb-4">{firstRelevantFile.filename.split('/').pop()}</p>
                        <a
                          href={getFileUrl()}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 transition-colors"
                        >
                          <FileSpreadsheet className="w-4 h-4" />
                          Download Excel
                        </a>
                      </div>
                    </div>
                  ) : (
                    <PDFViewer pdfUrl={getFileUrl()} compact={true} />
                  )
                ) : (
                  <div className="h-full flex items-center justify-center text-gray-400">
                    <div className="text-center p-6">
                      <FileText className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                      <p className="text-sm">No source files available for this statement type</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right - Answer Key Editor */}
            <div className="col-span-5 bg-white rounded-xl border border-gray-200 overflow-hidden flex flex-col">
              <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-gray-900">
                      {selectedPeriod?.period_label || 'Select a period'}
                    </h3>
                    <p className="text-xs text-gray-500">
                      {selectedStatementType === 'income' ? 'Income Statement' : 'Balance Sheet'} • 
                      {selectedStatement ? ` ${Object.keys(selectedStatement.expected).length} fields` : ' No data'}
                    </p>
                  </div>
                  <div className={`px-2 py-1 rounded text-xs font-medium ${
                    selectedStatementType === 'income' 
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-emerald-100 text-emerald-700'
                  }`}>
                    {selectedStatementType === 'income' ? 'IS' : 'BS'}
                  </div>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4">
                {selectedStatement && selectedStatement.expected ? (
                  <div className="space-y-3">
                    {Object.entries(selectedStatement.expected).map(([fieldName, field]) => (
                      <FieldEditor
                        key={fieldName}
                        fieldName={fieldName}
                        displayName={FIELD_DISPLAY_NAMES[fieldName] || fieldName}
                        field={field}
                        onChange={(property, value) => 
                          handleFieldChange(selectedPeriodIndex, selectedStatementType, fieldName, property, value)
                        }
                      />
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-400">
                    <div className="text-center">
                      <AlertCircle className="w-10 h-10 mx-auto text-gray-300 mb-3" />
                      <p className="text-sm">No expected values defined for this statement</p>
                      <p className="text-xs mt-1">Select a different period or statement type</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// Field Editor Component
interface FieldEditorProps {
  fieldName: string;
  displayName: string;
  field: ExpectedLineItem;
  onChange: (property: keyof ExpectedLineItem, value: any) => void;
}

const FieldEditor: React.FC<FieldEditorProps> = ({ fieldName, displayName, field, onChange }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className={`border rounded-lg transition-all ${
      field.required ? 'border-violet-200 bg-violet-50/30' : 'border-gray-200 bg-white'
    }`}>
      {/* Header Row */}
      <div className="flex items-center gap-2 p-3">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-gray-400 hover:text-gray-600"
        >
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-gray-900">{displayName}</span>
            {field.required && (
              <span className="text-[10px] px-1.5 py-0.5 bg-violet-100 text-violet-700 rounded font-medium">
                Required
              </span>
            )}
          </div>
          <div className="text-[10px] text-gray-400 font-mono">{fieldName}</div>
        </div>

        {/* Value Input - Always visible */}
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={field.value ?? ''}
            onChange={(e) => onChange('value', e.target.value)}
            placeholder="null"
            className={`w-32 px-3 py-1.5 border rounded-lg text-sm text-right font-mono ${
              field.value === null
                ? 'bg-gray-50 border-gray-200 text-gray-400 italic'
                : 'bg-white border-gray-300 text-gray-900'
            }`}
          />
          <button
            onClick={() => onChange('value', null)}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
            title="Set to null"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-0 space-y-3 border-t border-gray-100 mt-2">
          {/* Tolerance & Required Row */}
          <div className="flex items-center gap-4 pt-2">
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500">Tolerance:</label>
              <input
                type="number"
                value={field.tolerance_percent}
                onChange={(e) => onChange('tolerance_percent', e.target.value)}
                className="w-16 px-2 py-1 border border-gray-300 rounded text-xs text-right"
                min="0"
                max="100"
                step="0.5"
              />
              <span className="text-xs text-gray-400">%</span>
            </div>
            
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={field.required}
                onChange={(e) => onChange('required', e.target.checked)}
                className="w-4 h-4 text-violet-600 border-gray-300 rounded focus:ring-violet-500"
              />
              <span className="text-xs text-gray-600">Required field</span>
            </label>
          </div>

          {/* Notes */}
          <div>
            <label className="text-xs text-gray-500 block mb-1">Notes:</label>
            <textarea
              value={field.notes || ''}
              onChange={(e) => onChange('notes', e.target.value)}
              placeholder="Add notes about source, calculation, etc."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs resize-none"
              rows={2}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default AnswerKeyEditorPage;
