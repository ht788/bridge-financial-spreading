/**
 * Type definitions for the financial spreader application
 */

export interface LineItem {
  value: number | null;
  confidence: number;
  raw_fields_used: string[];
  source_section_hint: string | null;
}

export interface IncomeStatement {
  revenue: LineItem;
  cogs: LineItem;
  gross_profit: LineItem;
  sga: LineItem;
  research_and_development: LineItem;
  depreciation_amortization: LineItem;
  other_operating_expenses: LineItem;
  total_operating_expenses: LineItem;
  operating_income: LineItem;
  interest_expense: LineItem;
  interest_income: LineItem;
  other_income_expense: LineItem;
  pretax_income: LineItem;
  income_tax_expense: LineItem;
  net_income: LineItem;
  fiscal_period?: string;
  currency?: string;
  scale?: string;
}

export interface BalanceSheet {
  cash_and_equivalents: LineItem;
  short_term_investments: LineItem;
  accounts_receivable: LineItem;
  inventory: LineItem;
  prepaid_expenses: LineItem;
  other_current_assets: LineItem;
  total_current_assets: LineItem;
  ppe_gross: LineItem;
  accumulated_depreciation: LineItem;
  ppe_net: LineItem;
  intangible_assets: LineItem;
  goodwill: LineItem;
  long_term_investments: LineItem;
  other_non_current_assets: LineItem;
  total_non_current_assets: LineItem;
  total_assets: LineItem;
  accounts_payable: LineItem;
  short_term_debt: LineItem;
  accrued_expenses: LineItem;
  deferred_revenue_current: LineItem;
  other_current_liabilities: LineItem;
  total_current_liabilities: LineItem;
  long_term_debt: LineItem;
  deferred_tax_liabilities: LineItem;
  pension_liabilities: LineItem;
  other_non_current_liabilities: LineItem;
  total_non_current_liabilities: LineItem;
  total_liabilities: LineItem;
  common_stock: LineItem;
  additional_paid_in_capital: LineItem;
  retained_earnings: LineItem;
  treasury_stock: LineItem;
  accumulated_other_comprehensive_income: LineItem;
  total_shareholders_equity: LineItem;
  total_liabilities_and_equity: LineItem;
  as_of_date?: string;
  currency?: string;
  scale?: string;
}

export type FinancialStatement = IncomeStatement | BalanceSheet;

// =============================================================================
// MULTI-PERIOD TYPES
// =============================================================================

export interface PeriodData {
  period_label: string;
  end_date?: string | null;
  pdf_url?: string;
  original_filename?: string;
}

export interface IncomeStatementPeriod extends PeriodData {
  data: IncomeStatement;
}

export interface BalanceSheetPeriod extends PeriodData {
  data: BalanceSheet;
}

export interface MultiPeriodIncomeStatement {
  periods: IncomeStatementPeriod[];
  currency?: string;
  scale?: string;
}

export interface MultiPeriodBalanceSheet {
  periods: BalanceSheetPeriod[];
  currency?: string;
  scale?: string;
}

export type MultiPeriodFinancialStatement = MultiPeriodIncomeStatement | MultiPeriodBalanceSheet;

// =============================================================================
// COMBINED EXTRACTION TYPES (Auto-Detect Mode)
// =============================================================================

export interface StatementTypeDetection {
  has_income_statement: boolean;
  has_balance_sheet: boolean;
  income_statement_pages: number[];
  balance_sheet_pages: number[];
  confidence: number;
  income_statement_confidence: number;
  balance_sheet_confidence: number;
  notes?: string | null;
}

export interface CombinedFinancialExtraction {
  income_statement: MultiPeriodIncomeStatement | null;
  balance_sheet: MultiPeriodBalanceSheet | null;
  detected_types: StatementTypeDetection;
  extraction_metadata: Record<string, unknown>;
}

/**
 * Type guard to check if data is multi-period format
 */
export function isMultiPeriod(data: FinancialStatement | MultiPeriodFinancialStatement | CombinedFinancialExtraction): data is MultiPeriodFinancialStatement {
  return 'periods' in data && Array.isArray(data.periods);
}

/**
 * Type guard to check if data is combined extraction format (from auto-detect mode)
 */
export function isCombinedExtraction(data: unknown): data is CombinedFinancialExtraction {
  if (!data || typeof data !== 'object') return false;
  return 'detected_types' in data && ('income_statement' in data || 'balance_sheet' in data);
}

/**
 * Type guard to check if multi-period data is income statement
 */
export function isMultiPeriodIncome(data: MultiPeriodFinancialStatement): data is MultiPeriodIncomeStatement {
  return data.periods.length > 0 && 'revenue' in (data.periods[0] as any).data;
}

export interface SpreadMetadata {
  total_fields: number;
  high_confidence: number;
  medium_confidence: number;
  low_confidence: number;
  missing: number;
  extraction_rate: number;
  average_confidence: number;
  original_filename: string;
  job_id: string;
  pdf_url: string;
  doc_type?: string;
  // Auto-detect mode additional metadata
  is_combined?: boolean;
  detected_income_statement?: boolean;
  detected_balance_sheet?: boolean;
  statement_types_extracted?: string[];
  execution_time_seconds?: number;
  parallel_extraction?: boolean;
}

export interface SpreadResponse {
  success: boolean;
  job_id: string;
  data: FinancialStatement | MultiPeriodFinancialStatement | CombinedFinancialExtraction | null;
  error?: string;
  metadata: SpreadMetadata;
}

export type DocType = 'income' | 'balance' | 'auto';

export interface SpreadRequest {
  file: File;
  doc_type: DocType;
  period?: string;
  max_pages?: number;
  dpi?: number;
  model_override?: string;
}

// =============================================================================
// MULTI-FILE UPLOAD TYPES
// =============================================================================

export interface FileUploadItem {
  id: string;
  file: File;
  docType: DocType;
  status: 'pending' | 'processing' | 'success' | 'error';
  progress: number;
  result?: SpreadResponse;
  error?: string;
}

export interface BatchSpreadRequest {
  files: Array<{
    file: File;
    doc_type: DocType;
  }>;
  period?: string;
  max_pages?: number;
  dpi?: number;
}

export interface BatchSpreadResponse {
  batch_id: string;
  total_files: number;
  completed: number;
  failed: number;
  results: Array<{
    filename: string;
    success: boolean;
    data?: FinancialStatement | MultiPeriodFinancialStatement | CombinedFinancialExtraction;
    error?: string;
    metadata?: SpreadMetadata;
    job_id?: string;
  }>;
}

// =============================================================================
// LOGGING & DEBUG TYPES
// =============================================================================

export type LogLevel = 'debug' | 'info' | 'warning' | 'error';

export interface LogEntry {
  id: string;
  timestamp: string;
  level: LogLevel;
  message: string;
  source?: string;
  job_id?: string;
  filename?: string;
  details?: Record<string, unknown>;
  stackTrace?: string;
}

export interface ProcessingStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  startTime?: string;
  endTime?: string;
  duration?: number;
  details?: Record<string, unknown>;
}

export interface WebSocketMessage {
  type: 'log' | 'progress' | 'step' | 'error' | 'complete';
  job_id: string;
  timestamp: string;
  payload: LogEntry | ProcessingStep | { status: string; message: string };
}