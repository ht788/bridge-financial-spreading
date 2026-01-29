"""
Test Models for Financial Spreader Evaluation System

This module defines the data structures for:
- Test configurations and company definitions
- Grading criteria and results
- Historical test run records
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from enum import Enum


class GradeLevel(str, Enum):
    """Grade classification levels"""
    PERFECT = "A+"      # 95-100%
    EXCELLENT = "A"     # 90-95%
    GOOD = "B"          # 80-90%
    FAIR = "C"          # 70-80%
    POOR = "D"          # 60-70%
    FAILING = "F"       # Below 60%


class FieldAccuracy(str, Enum):
    """Accuracy classification for individual fields"""
    EXACT_MATCH = "exact"           # Values match exactly
    WITHIN_TOLERANCE = "tolerance"   # Within acceptable tolerance (e.g., 1-5%)
    PARTIAL = "partial"              # Partially correct (e.g., sign wrong)
    MISSING = "missing"              # Field not extracted but expected
    EXTRA = "extra"                  # Field extracted but not expected
    WRONG = "wrong"                  # Significantly different value


# =============================================================================
# COMPANY & FILE DEFINITIONS
# =============================================================================

class TestFile(BaseModel):
    """A single test file definition"""
    filename: str = Field(description="Name of the PDF file")
    doc_type: str = Field(description="Document type: 'income', 'balance', or 'auto' for auto-detection")
    period: Optional[str] = Field(default=None, description="Expected period label")
    description: Optional[str] = Field(default=None, description="Description of this file")


class TestCompany(BaseModel):
    """A company with test files and answer keys"""
    id: str = Field(description="Unique company identifier")
    name: str = Field(description="Company display name")
    files: List[TestFile] = Field(description="List of test files for this company")
    answer_key_path: Optional[str] = Field(default=None, description="Path to answer key JSON")


# =============================================================================
# ANSWER KEY STRUCTURE
# =============================================================================

class ExpectedLineItem(BaseModel):
    """Expected value for a single line item in the answer key"""
    value: Optional[float] = Field(default=None, description="Expected value")
    tolerance_percent: float = Field(default=5.0, description="Acceptable tolerance percentage")
    required: bool = Field(default=False, description="Whether this field is required")
    notes: Optional[str] = Field(default=None, description="Notes about this expected value")


class ExpectedIncomeStatement(BaseModel):
    """Expected income statement values from answer key"""
    revenue: Optional[ExpectedLineItem] = None
    cogs: Optional[ExpectedLineItem] = None
    gross_profit: Optional[ExpectedLineItem] = None
    sga: Optional[ExpectedLineItem] = None
    research_and_development: Optional[ExpectedLineItem] = None
    depreciation_amortization: Optional[ExpectedLineItem] = None
    other_operating_expenses: Optional[ExpectedLineItem] = None
    total_operating_expenses: Optional[ExpectedLineItem] = None
    operating_income: Optional[ExpectedLineItem] = None
    interest_expense: Optional[ExpectedLineItem] = None
    interest_income: Optional[ExpectedLineItem] = None
    other_income_expense: Optional[ExpectedLineItem] = None
    pretax_income: Optional[ExpectedLineItem] = None
    income_tax_expense: Optional[ExpectedLineItem] = None
    net_income: Optional[ExpectedLineItem] = None


class ExpectedBalanceSheet(BaseModel):
    """Expected balance sheet values from answer key"""
    cash_and_equivalents: Optional[ExpectedLineItem] = None
    short_term_investments: Optional[ExpectedLineItem] = None
    accounts_receivable: Optional[ExpectedLineItem] = None
    inventory: Optional[ExpectedLineItem] = None
    prepaid_expenses: Optional[ExpectedLineItem] = None
    other_current_assets: Optional[ExpectedLineItem] = None
    total_current_assets: Optional[ExpectedLineItem] = None
    ppe_gross: Optional[ExpectedLineItem] = None
    accumulated_depreciation: Optional[ExpectedLineItem] = None
    ppe_net: Optional[ExpectedLineItem] = None
    intangible_assets: Optional[ExpectedLineItem] = None
    goodwill: Optional[ExpectedLineItem] = None
    long_term_investments: Optional[ExpectedLineItem] = None
    other_non_current_assets: Optional[ExpectedLineItem] = None
    total_non_current_assets: Optional[ExpectedLineItem] = None
    total_assets: Optional[ExpectedLineItem] = None
    accounts_payable: Optional[ExpectedLineItem] = None
    short_term_debt: Optional[ExpectedLineItem] = None
    accrued_expenses: Optional[ExpectedLineItem] = None
    deferred_revenue_current: Optional[ExpectedLineItem] = None
    other_current_liabilities: Optional[ExpectedLineItem] = None
    total_current_liabilities: Optional[ExpectedLineItem] = None
    long_term_debt: Optional[ExpectedLineItem] = None
    deferred_tax_liabilities: Optional[ExpectedLineItem] = None
    pension_liabilities: Optional[ExpectedLineItem] = None
    other_non_current_liabilities: Optional[ExpectedLineItem] = None
    total_non_current_liabilities: Optional[ExpectedLineItem] = None
    total_liabilities: Optional[ExpectedLineItem] = None
    common_stock: Optional[ExpectedLineItem] = None
    additional_paid_in_capital: Optional[ExpectedLineItem] = None
    retained_earnings: Optional[ExpectedLineItem] = None
    treasury_stock: Optional[ExpectedLineItem] = None
    accumulated_other_comprehensive_income: Optional[ExpectedLineItem] = None
    total_shareholders_equity: Optional[ExpectedLineItem] = None
    total_liabilities_and_equity: Optional[ExpectedLineItem] = None


class PeriodAnswerKey(BaseModel):
    """Answer key for a single period"""
    period_label: str = Field(description="Period label (e.g., '2024', 'Jan 2025')")
    doc_type: str = Field(description="Document type: 'income' or 'balance'")
    expected: Dict[str, ExpectedLineItem] = Field(
        default_factory=dict,
        description="Expected values keyed by field name"
    )


class FileAnswerKey(BaseModel):
    """Complete answer key for a single file (potentially multi-period)"""
    filename: str = Field(description="Name of the file this answer key is for")
    doc_type: str = Field(description="Document type: 'income' or 'balance'")
    periods: List[PeriodAnswerKey] = Field(
        default_factory=list,
        description="Answer keys for each period in the file"
    )


class CompanyAnswerKey(BaseModel):
    """Complete answer key for a company"""
    company_id: str
    company_name: str
    files: List[FileAnswerKey] = Field(default_factory=list)


# =============================================================================
# GRADING RESULTS
# =============================================================================

class FieldComparison(BaseModel):
    """Detailed comparison result for a single field"""
    field_name: str
    expected_value: Optional[float]
    extracted_value: Optional[float]
    accuracy: FieldAccuracy
    score: float = Field(ge=0.0, le=1.0, description="Score from 0-1")
    tolerance_used: float = Field(description="Tolerance percentage used")
    difference: Optional[float] = Field(default=None, description="Absolute difference")
    difference_percent: Optional[float] = Field(default=None, description="Percentage difference")
    notes: Optional[str] = None


class PeriodGrade(BaseModel):
    """Grading results for a single period"""
    period_label: str
    doc_type: str
    total_fields: int
    matched_fields: int
    partial_fields: int
    missing_fields: int
    wrong_fields: int
    extra_fields: int
    score: float = Field(ge=0.0, le=100.0, description="Overall score 0-100")
    grade: GradeLevel
    field_comparisons: List[FieldComparison] = Field(default_factory=list)


class FileGrade(BaseModel):
    """Grading results for a single file"""
    filename: str
    doc_type: str
    periods: List[PeriodGrade] = Field(default_factory=list)
    overall_score: float = Field(ge=0.0, le=100.0)
    overall_grade: GradeLevel


class TestRunResult(BaseModel):
    """Complete results from a single test run"""
    id: str = Field(description="Unique test run ID")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Configuration used
    company_id: str
    company_name: str
    model_name: str
    prompt_version: Optional[str] = None
    prompt_content: Optional[str] = None
    
    # Overall results
    overall_score: float = Field(ge=0.0, le=100.0)
    overall_grade: GradeLevel
    
    # Per-file results
    file_results: List[FileGrade] = Field(default_factory=list)
    
    # Summary stats
    total_files: int = 0
    total_periods: int = 0
    total_fields_tested: int = 0
    fields_correct: int = 0
    fields_partial: int = 0
    fields_wrong: int = 0
    fields_missing: int = 0
    
    # Execution metadata
    execution_time_seconds: float = 0.0
    error: Optional[str] = None
    fallback_prompt_used: bool = Field(
        default=False, 
        description="Whether fallback prompt was used during extraction"
    )
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# TEST CONFIGURATION & REQUEST MODELS
# =============================================================================

class TestRunConfig(BaseModel):
    """Configuration for executing a test run"""
    company_id: str = Field(description="Company to test")
    model_name: str = Field(default="claude-opus-4-5", description="Model to use for extraction")
    prompt_override: Optional[str] = Field(
        default=None, 
        description="Custom prompt to use instead of Hub prompt"
    )
    extended_thinking: bool = Field(
        default=False,
        description="Enable extended thinking for Anthropic models (ignored for OpenAI)"
    )
    dpi: int = Field(default=150, description="PDF conversion DPI (optimized for speed while preserving number readability)")
    max_pages: Optional[int] = Field(default=None, description="Max pages per file")
    tolerance_percent: float = Field(default=5.0, description="Default tolerance for comparisons")
    
    # Parallel processing configuration
    parallel: bool = Field(
        default=True,
        description="Enable parallel file processing for faster test execution"
    )
    max_concurrent: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of concurrent file extractions (1-10, default 3)"
    )


class TestRunSummary(BaseModel):
    """Summary of a test run for the history table"""
    id: str
    timestamp: datetime
    company_id: str
    company_name: str
    model_name: str
    prompt_version: Optional[str]
    overall_score: float
    overall_grade: GradeLevel
    total_files: int
    execution_time_seconds: float


class TestHistoryResponse(BaseModel):
    """Response containing test history"""
    runs: List[TestRunSummary]
    total_count: int


# =============================================================================
# API RESPONSE MODELS
# =============================================================================

class AvailableModel(BaseModel):
    """A model available for testing"""
    id: str
    name: str
    description: Optional[str] = None


class TestingStatusResponse(BaseModel):
    """Status response for the testing system"""
    available_companies: List[TestCompany]
    available_models: List[AvailableModel]
    current_prompt_content: Optional[str] = None


def score_to_grade(score: float) -> GradeLevel:
    """Convert a numerical score (0-100) to a grade level"""
    if score >= 95:
        return GradeLevel.PERFECT
    elif score >= 90:
        return GradeLevel.EXCELLENT
    elif score >= 80:
        return GradeLevel.GOOD
    elif score >= 70:
        return GradeLevel.FAIR
    elif score >= 60:
        return GradeLevel.POOR
    else:
        return GradeLevel.FAILING
