"""
models.py - The Contract Layer

This module defines the rigid data structures that enforce schema validation
for financial statement spreading. These Pydantic models serve as the "contract"
between the LLM output and our application.

Architecture Decision:
- Field descriptions provide hints to the model, but the core extraction logic
  lives in LangSmith prompts (pulled via hub.pull()). This separation allows:
  1. Prompt engineers to iterate without code deploys
  2. Schema enforcement to remain stable in code
  3. Clear boundaries between "what to extract" (prompts) and "what shape" (models)
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    """
    Reusable model for a single financial line item.
    
    This structure captures not just the value, but the provenance and confidence
    of the extraction - critical for audit trails in financial applications.
    """
    
    value: Optional[float] = Field(
        default=None,
        description="The standardized dollar amount. None if not found or not applicable."
    )
    
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score from 0.0 (no confidence) to 1.0 (certain). "
                    "Use 0.5 for inferred values, 0.8+ for clearly stated amounts."
    )
    
    raw_fields_used: List[str] = Field(
        default_factory=list,
        description="Exact text snippets from the source document used to derive this value. "
                    "Critical for audit trail and debugging extraction issues."
    )
    
    source_section_hint: Optional[str] = Field(
        default=None,
        description="The section header or category under which this item was found "
                    "(e.g., 'Operating Expenses', 'Current Assets'). Helps with validation."
    )


# =============================================================================
# INCOME STATEMENT SCHEMA
# =============================================================================

class IncomeStatement(BaseModel):
    """
    Standardized Income Statement schema for financial spreading.
    
    This schema maps various naming conventions (Revenue, Sales, Net Sales, 
    Total Income) to canonical field names. The LangSmith prompt handles
    the mapping logic; this schema enforces the output structure.
    
    Fields follow the standard income statement hierarchy:
    Revenue → Gross Profit → Operating Income → Net Income
    """
    
    # --- Revenue Section ---
    revenue: LineItem = Field(
        default_factory=LineItem,
        description="Total revenue/sales/net sales. The top-line figure."
    )
    
    # --- Cost of Goods Sold ---
    cogs: LineItem = Field(
        default_factory=LineItem,
        description="Cost of Goods Sold / Cost of Sales / Cost of Revenue. "
                    "Direct costs attributable to production."
    )
    
    gross_profit: LineItem = Field(
        default_factory=LineItem,
        description="Gross Profit = Revenue - COGS. May be stated or calculated."
    )
    
    # --- Operating Expenses ---
    sga: LineItem = Field(
        default_factory=LineItem,
        description="Selling, General & Administrative expenses. "
                    "May be broken out or combined."
    )
    
    research_and_development: LineItem = Field(
        default_factory=LineItem,
        description="R&D expenses. Common in tech/pharma companies."
    )
    
    depreciation_amortization: LineItem = Field(
        default_factory=LineItem,
        description="Depreciation and Amortization. May be in COGS, OpEx, or separate. "
                    "Note the source_section_hint for where it was found."
    )
    
    other_operating_expenses: LineItem = Field(
        default_factory=LineItem,
        description="Catch-all for operating expenses not categorized above."
    )
    
    total_operating_expenses: LineItem = Field(
        default_factory=LineItem,
        description="Sum of all operating expenses. May be stated or calculated."
    )
    
    operating_income: LineItem = Field(
        default_factory=LineItem,
        description="Operating Income / EBIT. Gross Profit - Operating Expenses."
    )
    
    # --- Non-Operating Items ---
    interest_expense: LineItem = Field(
        default_factory=LineItem,
        description="Interest expense on debt. Critical for coverage ratios."
    )
    
    interest_income: LineItem = Field(
        default_factory=LineItem,
        description="Interest income from investments/cash."
    )
    
    other_income_expense: LineItem = Field(
        default_factory=LineItem,
        description="Non-operating income/expenses (gains, losses, etc.)."
    )
    
    # --- Pre-Tax and Tax ---
    pretax_income: LineItem = Field(
        default_factory=LineItem,
        description="Earnings Before Tax (EBT). Operating Income ± Non-Operating Items."
    )
    
    income_tax_expense: LineItem = Field(
        default_factory=LineItem,
        description="Income tax expense/provision."
    )
    
    # --- Net Income ---
    net_income: LineItem = Field(
        default_factory=LineItem,
        description="Net Income / Net Profit / Bottom Line. The final profit figure."
    )
    
    # --- Metadata ---
    fiscal_period: Optional[str] = Field(
        default=None,
        description="The fiscal period this statement covers (e.g., 'FY2024', 'Q3 2024')."
    )
    
    currency: Optional[str] = Field(
        default="USD",
        description="Currency of the amounts (ISO 4217 code)."
    )
    
    scale: Optional[str] = Field(
        default="units",
        description="Scale of numbers: 'units', 'thousands', 'millions', 'billions'."
    )


# =============================================================================
# BALANCE SHEET SCHEMA
# =============================================================================

class BalanceSheet(BaseModel):
    """
    Standardized Balance Sheet schema for financial spreading.
    
    This schema enforces the fundamental accounting equation:
    Assets = Liabilities + Shareholders' Equity
    
    Fields are organized by standard balance sheet sections:
    Current Assets → Non-Current Assets → Current Liabilities → 
    Long-Term Liabilities → Shareholders' Equity
    """
    
    # --- Current Assets ---
    cash_and_equivalents: LineItem = Field(
        default_factory=LineItem,
        description="Cash and Cash Equivalents. Most liquid assets."
    )
    
    short_term_investments: LineItem = Field(
        default_factory=LineItem,
        description="Marketable securities and short-term investments."
    )
    
    accounts_receivable: LineItem = Field(
        default_factory=LineItem,
        description="Accounts Receivable / Trade Receivables (net of allowance)."
    )
    
    inventory: LineItem = Field(
        default_factory=LineItem,
        description="Total Inventory (raw materials, WIP, finished goods)."
    )
    
    prepaid_expenses: LineItem = Field(
        default_factory=LineItem,
        description="Prepaid expenses and other current assets."
    )
    
    other_current_assets: LineItem = Field(
        default_factory=LineItem,
        description="Other current assets not categorized above."
    )
    
    total_current_assets: LineItem = Field(
        default_factory=LineItem,
        description="Sum of all current assets."
    )
    
    # --- Non-Current Assets ---
    ppe_gross: LineItem = Field(
        default_factory=LineItem,
        description="Property, Plant & Equipment at gross/cost."
    )
    
    accumulated_depreciation: LineItem = Field(
        default_factory=LineItem,
        description="Accumulated Depreciation (typically negative or shown as deduction)."
    )
    
    ppe_net: LineItem = Field(
        default_factory=LineItem,
        description="Net PP&E = Gross PP&E - Accumulated Depreciation."
    )
    
    intangible_assets: LineItem = Field(
        default_factory=LineItem,
        description="Intangible assets (patents, trademarks, etc.)."
    )
    
    goodwill: LineItem = Field(
        default_factory=LineItem,
        description="Goodwill from acquisitions."
    )
    
    long_term_investments: LineItem = Field(
        default_factory=LineItem,
        description="Long-term investments and equity method investments."
    )
    
    other_non_current_assets: LineItem = Field(
        default_factory=LineItem,
        description="Other long-term assets (deferred tax assets, etc.)."
    )
    
    total_non_current_assets: LineItem = Field(
        default_factory=LineItem,
        description="Sum of all non-current assets."
    )
    
    total_assets: LineItem = Field(
        default_factory=LineItem,
        description="Total Assets = Current + Non-Current Assets."
    )
    
    # --- Current Liabilities ---
    accounts_payable: LineItem = Field(
        default_factory=LineItem,
        description="Accounts Payable / Trade Payables."
    )
    
    short_term_debt: LineItem = Field(
        default_factory=LineItem,
        description="Short-term borrowings / Current portion of long-term debt."
    )
    
    accrued_expenses: LineItem = Field(
        default_factory=LineItem,
        description="Accrued expenses and other current liabilities."
    )
    
    deferred_revenue_current: LineItem = Field(
        default_factory=LineItem,
        description="Current portion of deferred/unearned revenue."
    )
    
    other_current_liabilities: LineItem = Field(
        default_factory=LineItem,
        description="Other current liabilities not categorized above."
    )
    
    total_current_liabilities: LineItem = Field(
        default_factory=LineItem,
        description="Sum of all current liabilities."
    )
    
    # --- Non-Current Liabilities ---
    long_term_debt: LineItem = Field(
        default_factory=LineItem,
        description="Long-term debt / Notes payable (non-current portion)."
    )
    
    deferred_tax_liabilities: LineItem = Field(
        default_factory=LineItem,
        description="Deferred tax liabilities."
    )
    
    pension_liabilities: LineItem = Field(
        default_factory=LineItem,
        description="Pension and post-retirement benefit obligations."
    )
    
    other_non_current_liabilities: LineItem = Field(
        default_factory=LineItem,
        description="Other long-term liabilities."
    )
    
    total_non_current_liabilities: LineItem = Field(
        default_factory=LineItem,
        description="Sum of all non-current liabilities."
    )
    
    total_liabilities: LineItem = Field(
        default_factory=LineItem,
        description="Total Liabilities = Current + Non-Current Liabilities."
    )
    
    # --- Shareholders' Equity ---
    common_stock: LineItem = Field(
        default_factory=LineItem,
        description="Common stock at par value."
    )
    
    additional_paid_in_capital: LineItem = Field(
        default_factory=LineItem,
        description="Additional Paid-In Capital / Share Premium."
    )
    
    retained_earnings: LineItem = Field(
        default_factory=LineItem,
        description="Retained Earnings / Accumulated Deficit."
    )
    
    treasury_stock: LineItem = Field(
        default_factory=LineItem,
        description="Treasury Stock (typically negative)."
    )
    
    accumulated_other_comprehensive_income: LineItem = Field(
        default_factory=LineItem,
        description="AOCI - Unrealized gains/losses not in net income."
    )
    
    total_shareholders_equity: LineItem = Field(
        default_factory=LineItem,
        description="Total Shareholders' Equity / Net Worth."
    )
    
    total_liabilities_and_equity: LineItem = Field(
        default_factory=LineItem,
        description="Total Liabilities + Equity. Must equal Total Assets."
    )
    
    # --- Metadata ---
    as_of_date: Optional[str] = Field(
        default=None,
        description="The date this balance sheet represents (e.g., '2024-12-31')."
    )
    
    currency: Optional[str] = Field(
        default="USD",
        description="Currency of the amounts (ISO 4217 code)."
    )
    
    scale: Optional[str] = Field(
        default="units",
        description="Scale of numbers: 'units', 'thousands', 'millions', 'billions'."
    )


# =============================================================================
# MULTI-PERIOD WRAPPERS
# =============================================================================

class PeriodData(BaseModel):
    """
    A single period's worth of financial data.
    
    This wraps either an IncomeStatement or BalanceSheet with its
    period label, allowing for multi-period comparisons.
    """
    period_label: str = Field(
        description="Human-readable period label (e.g., 'FY2024', 'Year Ended Dec 31, 2024')"
    )
    end_date: Optional[str] = Field(
        default=None,
        description="ISO date (YYYY-MM-DD) for this period's end date, if known"
    )


class IncomeStatementPeriod(PeriodData):
    """Income statement data for a single period."""
    data: IncomeStatement


class BalanceSheetPeriod(PeriodData):
    """Balance sheet data for a single period."""
    data: BalanceSheet


# =============================================================================
# MULTI-PERIOD EXTRACTION OUTPUT (for single LLM call)
# =============================================================================

class MultiPeriodIncomeExtraction(BaseModel):
    """
    Output schema for extracting ALL periods from an income statement in a single LLM call.
    
    This allows the model to extract data for all visible period columns at once,
    which is more efficient and provides better context for accurate extraction.
    """
    periods: List[IncomeStatementPeriod] = Field(
        description="List of income statement data for each period column found in the document. "
                    "Extract data for ALL visible period columns (e.g., 'Jan 2025' AND 'Jan-Dec 2024'). "
                    "Order from most recent (index 0) to oldest."
    )
    currency: Optional[str] = Field(
        default="USD",
        description="Currency for all periods (ISO 4217 code)"
    )
    scale: Optional[str] = Field(
        default="units",
        description="Scale of numbers: 'units', 'thousands', 'millions', 'billions'"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Any notes about the extraction (e.g., assumptions made, ambiguous values)"
    )


class MultiPeriodBalanceExtraction(BaseModel):
    """
    Output schema for extracting ALL periods from a balance sheet in a single LLM call.
    
    This allows the model to extract data for all visible as-of date columns at once,
    which is more efficient and provides better context for accurate extraction.
    """
    periods: List[BalanceSheetPeriod] = Field(
        description="List of balance sheet data for each as-of date column found in the document. "
                    "Extract data for ALL visible date columns. "
                    "Order from most recent (index 0) to oldest."
    )
    currency: Optional[str] = Field(
        default="USD",
        description="Currency for all periods (ISO 4217 code)"
    )
    scale: Optional[str] = Field(
        default="units",
        description="Scale of numbers: 'units', 'thousands', 'millions', 'billions'"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Any notes about the extraction (e.g., assumptions made, ambiguous values)"
    )


class MultiPeriodIncomeStatement(BaseModel):
    """
    Multi-period Income Statement for comparative analysis.
    
    Periods are ordered from most recent (index 0) to oldest.
    This allows side-by-side comparison of multiple fiscal periods.
    """
    periods: List[IncomeStatementPeriod] = Field(
        default_factory=list,
        description="List of income statements, one per period, ordered most recent first"
    )
    currency: Optional[str] = Field(
        default="USD",
        description="Currency for all periods (assumed consistent)"
    )
    scale: Optional[str] = Field(
        default="units",
        description="Scale for all periods (assumed consistent)"
    )
    
    @property
    def period_labels(self) -> List[str]:
        """Get list of period labels in order."""
        return [p.period_label for p in self.periods]
    
    @property
    def num_periods(self) -> int:
        """Get number of periods."""
        return len(self.periods)


class MultiPeriodBalanceSheet(BaseModel):
    """
    Multi-period Balance Sheet for comparative analysis.
    
    Periods are ordered from most recent (index 0) to oldest.
    This allows side-by-side comparison of multiple as-of dates.
    """
    periods: List[BalanceSheetPeriod] = Field(
        default_factory=list,
        description="List of balance sheets, one per period, ordered most recent first"
    )
    currency: Optional[str] = Field(
        default="USD",
        description="Currency for all periods (assumed consistent)"
    )
    scale: Optional[str] = Field(
        default="units",
        description="Scale for all periods (assumed consistent)"
    )
    
    @property
    def period_labels(self) -> List[str]:
        """Get list of period labels in order."""
        return [p.period_label for p in self.periods]
    
    @property
    def num_periods(self) -> int:
        """Get number of periods."""
        return len(self.periods)


# =============================================================================
# STATEMENT TYPE DETECTION (Auto-Detection)
# =============================================================================

class StatementTypeDetection(BaseModel):
    """
    Result of automatic statement type detection from a financial document.
    
    This model captures which types of financial statements are present
    in a document, enabling automatic routing to the correct extraction pipeline.
    """
    has_income_statement: bool = Field(
        default=False,
        description="True if an income statement (P&L) is detected in the document"
    )
    has_balance_sheet: bool = Field(
        default=False,
        description="True if a balance sheet is detected in the document"
    )
    income_statement_pages: List[int] = Field(
        default_factory=list,
        description="1-indexed page numbers where income statement data is found"
    )
    balance_sheet_pages: List[int] = Field(
        default_factory=list,
        description="1-indexed page numbers where balance sheet data is found"
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the detection (0.0-1.0)"
    )
    income_statement_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence specifically for income statement detection"
    )
    balance_sheet_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence specifically for balance sheet detection"
    )
    notes: Optional[str] = Field(
        default=None,
        description="Additional notes about the detection (e.g., assumptions made, ambiguities)"
    )


class CombinedFinancialExtraction(BaseModel):
    """
    Combined extraction result when a document contains both income statement
    and balance sheet data.
    
    This model enables parallel extraction of both statement types from a
    single document upload, improving efficiency for financial packets.
    """
    income_statement: Optional[MultiPeriodIncomeStatement] = Field(
        default=None,
        description="Extracted income statement data (if present in document)"
    )
    balance_sheet: Optional[MultiPeriodBalanceSheet] = Field(
        default=None,
        description="Extracted balance sheet data (if present in document)"
    )
    detected_types: StatementTypeDetection = Field(
        description="Detection results indicating which statement types were found"
    )
    extraction_metadata: dict = Field(
        default_factory=dict,
        description="Metadata about the extraction process (timing, model used, etc.)"
    )
    
    @property
    def has_both_statements(self) -> bool:
        """Check if both statement types were extracted."""
        return self.income_statement is not None and self.balance_sheet is not None
    
    @property
    def statement_types_extracted(self) -> List[str]:
        """Get list of statement types that were successfully extracted."""
        types = []
        if self.income_statement is not None:
            types.append("income")
        if self.balance_sheet is not None:
            types.append("balance")
        return types


# =============================================================================
# SCHEMA REGISTRY
# =============================================================================

# Maps document types to their corresponding Pydantic models
# Used by spreader.py to dynamically select the correct schema
SCHEMA_REGISTRY = {
    "income": IncomeStatement,
    "income_statement": IncomeStatement,
    "balance": BalanceSheet,
    "balance_sheet": BalanceSheet,
}

# Multi-period schema registry
MULTI_PERIOD_SCHEMA_REGISTRY = {
    "income": MultiPeriodIncomeStatement,
    "income_statement": MultiPeriodIncomeStatement,
    "balance": MultiPeriodBalanceSheet,
    "balance_sheet": MultiPeriodBalanceSheet,
}

# Multi-period EXTRACTION schema registry (for single LLM call)
MULTI_PERIOD_EXTRACTION_REGISTRY = {
    "income": MultiPeriodIncomeExtraction,
    "income_statement": MultiPeriodIncomeExtraction,
    "balance": MultiPeriodBalanceExtraction,
    "balance_sheet": MultiPeriodBalanceExtraction,
}


def get_schema_for_doc_type(doc_type: str) -> type[BaseModel]:
    """
    Retrieve the appropriate Pydantic schema for a document type.
    
    Args:
        doc_type: The type of financial document ('income' or 'balance')
        
    Returns:
        The corresponding Pydantic model class
        
    Raises:
        ValueError: If doc_type is not recognized
    """
    normalized = doc_type.lower().strip()
    if normalized not in SCHEMA_REGISTRY:
        valid_types = list(SCHEMA_REGISTRY.keys())
        raise ValueError(
            f"Unknown document type: '{doc_type}'. "
            f"Valid types are: {valid_types}"
        )
    return SCHEMA_REGISTRY[normalized]


def get_multi_period_schema_for_doc_type(doc_type: str) -> type[BaseModel]:
    """
    Retrieve the appropriate multi-period Pydantic schema for a document type.
    
    Args:
        doc_type: The type of financial document ('income' or 'balance')
        
    Returns:
        The corresponding multi-period Pydantic model class
        
    Raises:
        ValueError: If doc_type is not recognized
    """
    normalized = doc_type.lower().strip()
    if normalized not in MULTI_PERIOD_SCHEMA_REGISTRY:
        valid_types = list(MULTI_PERIOD_SCHEMA_REGISTRY.keys())
        raise ValueError(
            f"Unknown document type: '{doc_type}'. "
            f"Valid types are: {valid_types}"
        )
    return MULTI_PERIOD_SCHEMA_REGISTRY[normalized]


def get_multi_period_extraction_schema(doc_type: str) -> type[BaseModel]:
    """
    Retrieve the multi-period EXTRACTION schema for a document type.
    
    This schema is used for single-LLM-call extraction of all periods.
    
    Args:
        doc_type: The type of financial document ('income' or 'balance')
        
    Returns:
        The corresponding extraction schema class
        
    Raises:
        ValueError: If doc_type is not recognized
    """
    normalized = doc_type.lower().strip()
    if normalized not in MULTI_PERIOD_EXTRACTION_REGISTRY:
        valid_types = list(MULTI_PERIOD_EXTRACTION_REGISTRY.keys())
        raise ValueError(
            f"Unknown document type: '{doc_type}'. "
            f"Valid types are: {valid_types}"
        )
    return MULTI_PERIOD_EXTRACTION_REGISTRY[normalized]
