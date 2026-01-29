/**
 * TypeScript types for the Testing System
 */

// =============================================================================
// ENUMS
// =============================================================================

export type GradeLevel = 'A+' | 'A' | 'B' | 'C' | 'D' | 'F';

export type TestRunStatus = 'pending' | 'running' | 'complete' | 'error';

export type FieldAccuracy = 
  | 'exact' 
  | 'tolerance' 
  | 'partial' 
  | 'missing' 
  | 'extra' 
  | 'wrong';

// =============================================================================
// COMPANY & FILE DEFINITIONS
// =============================================================================

export interface TestFile {
  filename: string;
  doc_type: 'income' | 'balance' | 'auto';
  period?: string;
  description?: string;
}

export interface TestCompany {
  id: string;
  name: string;
  files: TestFile[];
  answer_key_path?: string;
}

export interface AvailableModel {
  id: string;
  name: string;
  description?: string;
}

// =============================================================================
// ANSWER KEY TYPES
// =============================================================================

export interface ExpectedLineItem {
  value: number | null;
  tolerance_percent: number;
  required: boolean;
  notes?: string;
}

export interface PeriodAnswerKey {
  period_label: string;
  doc_type: string;
  expected: Record<string, ExpectedLineItem>;
}

export interface FileAnswerKey {
  filename: string;
  doc_type: string;
  periods: PeriodAnswerKey[];
}

export interface CompanyAnswerKey {
  company_id: string;
  company_name: string;
  files: FileAnswerKey[];
}

// =============================================================================
// GRADING RESULTS
// =============================================================================

export interface FieldComparison {
  field_name: string;
  expected_value: number | null;
  extracted_value: number | null;
  accuracy: FieldAccuracy;
  score: number;
  tolerance_used: number;
  difference?: number;
  difference_percent?: number;
  notes?: string;
}

export interface PeriodGrade {
  period_label: string;
  doc_type: string;
  total_fields: number;
  matched_fields: number;
  partial_fields: number;
  missing_fields: number;
  wrong_fields: number;
  extra_fields: number;
  score: number;
  grade: GradeLevel;
  field_comparisons: FieldComparison[];
}

export interface FileGrade {
  filename: string;
  doc_type: string;
  periods: PeriodGrade[];
  overall_score: number;
  overall_grade: GradeLevel;
}

// =============================================================================
// TEST RUN TYPES
// =============================================================================

export interface TestRunConfig {
  company_id: string;
  model_name: string;
  prompt_override?: string;
  extended_thinking?: boolean;
  dpi?: number;
  max_pages?: number;
  tolerance_percent?: number;
  /** Enable parallel file processing for faster test execution (default: true) */
  parallel?: boolean;
  /** Maximum number of concurrent file extractions (1-10, default: 3) */
  max_concurrent?: number;
}

export interface TestRunResult {
  id: string;
  timestamp: string;
  company_id: string;
  company_name: string;
  model_name: string;
  prompt_version?: string;
  prompt_content?: string;
  status: TestRunStatus;
  overall_score: number;
  overall_grade: GradeLevel;
  file_results: FileGrade[];
  total_files: number;
  total_periods: number;
  total_fields_tested: number;
  fields_correct: number;
  fields_partial: number;
  fields_wrong: number;
  fields_missing: number;
  execution_time_seconds: number;
  error?: string;
  metadata: Record<string, unknown>;
  fallback_prompt_used?: boolean;
}

export interface TestRunSummary {
  id: string;
  timestamp: string;
  company_id: string;
  company_name: string;
  model_name: string;
  prompt_version?: string;
  status: TestRunStatus;
  overall_score: number;
  overall_grade: GradeLevel;
  total_files: number;
  execution_time_seconds: number;
}

export interface TestHistoryResponse {
  runs: TestRunSummary[];
  total_count: number;
}

// =============================================================================
// API RESPONSE TYPES
// =============================================================================

export interface TestingStatusResponse {
  available_companies: TestCompany[];
  available_models: AvailableModel[];
  current_prompt_content?: string;
}

// =============================================================================
// UI STATE TYPES
// =============================================================================

export interface TestingPageState {
  status: 'idle' | 'loading' | 'running' | 'complete' | 'error';
  selectedCompany?: TestCompany;
  selectedModel?: AvailableModel;
  promptContent?: string;
  currentResult?: TestRunResult;
  history: TestRunSummary[];
  error?: string;
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

export function getGradeColor(grade: GradeLevel): string {
  switch (grade) {
    case 'A+':
      return 'text-emerald-600 bg-emerald-50 border-emerald-200';
    case 'A':
      return 'text-green-600 bg-green-50 border-green-200';
    case 'B':
      return 'text-blue-600 bg-blue-50 border-blue-200';
    case 'C':
      return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'D':
      return 'text-orange-600 bg-orange-50 border-orange-200';
    case 'F':
      return 'text-red-600 bg-red-50 border-red-200';
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200';
  }
}

export function getAccuracyColor(accuracy: FieldAccuracy): string {
  switch (accuracy) {
    case 'exact':
      return 'text-emerald-600 bg-emerald-50';
    case 'tolerance':
      return 'text-green-600 bg-green-50';
    case 'partial':
      return 'text-yellow-600 bg-yellow-50';
    case 'missing':
      return 'text-red-600 bg-red-50';
    case 'wrong':
      return 'text-red-700 bg-red-100';
    case 'extra':
      return 'text-blue-600 bg-blue-50';
    default:
      return 'text-gray-600 bg-gray-50';
  }
}

export function getAccuracyLabel(accuracy: FieldAccuracy): string {
  switch (accuracy) {
    case 'exact':
      return 'Exact Match';
    case 'tolerance':
      return 'Within Tolerance';
    case 'partial':
      return 'Partial';
    case 'missing':
      return 'Missing';
    case 'wrong':
      return 'Wrong';
    case 'extra':
      return 'Extra';
    default:
      return accuracy;
  }
}

export function formatScore(score: number): string {
  return `${score.toFixed(1)}%`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

export function getStatusColor(status: TestRunStatus): string {
  switch (status) {
    case 'pending':
      return 'text-gray-600 bg-gray-50 border-gray-200';
    case 'running':
      return 'text-blue-600 bg-blue-50 border-blue-200';
    case 'complete':
      return 'text-green-600 bg-green-50 border-green-200';
    case 'error':
      return 'text-red-600 bg-red-50 border-red-200';
    default:
      return 'text-gray-600 bg-gray-50 border-gray-200';
  }
}

export function getStatusLabel(status: TestRunStatus): string {
  switch (status) {
    case 'pending':
      return 'Pending';
    case 'running':
      return 'Running';
    case 'complete':
      return 'Complete';
    case 'error':
      return 'Error';
    default:
      return status;
  }
}
