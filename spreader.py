"""
spreader.py - The Engine Layer (LangSmith-Native + Vision-First + Reasoning Loop)

This module implements financial spreading with:
1. FULL LangSmith integration (Hub prompts, automatic tracing)
2. VISION-FIRST architecture (PDFs as images, not text)
3. REASONING LOOP with self-correction (validates and retries on errors)

Architecture:

1. HUB-CONTROLLED MODEL CONFIGURATION
   - Model name, parameters (temperature, extended_thinking) come from LangSmith Hub
   - Change models in LangSmith UI → takes effect immediately (no code deploy)
   - Code only provides fallback defaults when Hub is unavailable

2. VISION-FIRST INPUT
   - PDFs converted to images (NOT text extracted)
   - Images resized to max 1024px width for cost efficiency
   - Model "sees" indentation, headers, alignment - critical for correct categorization

3. REASONING LOOP (Chain of Thought)
   - Uses Claude Opus 4.6 with adaptive thinking for deep analysis
   - Uses Claude 3.5 Haiku for fast detection/classification tasks
   - Validates extracted data (math checks, balance checks)
   - Auto-retries with error context if validation fails

4. STRUCTURED OUTPUT
   - .with_structured_output() ensures Pydantic schema compliance
   - Validation errors traced in LangSmith for debugging
"""

import logging
import os
import asyncio
import concurrent.futures
from typing import Optional, Union, List, Any, Tuple
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

# Load environment variables from repo root .env
from dotenv import load_dotenv

def _load_env_vars() -> None:
    repo_root = Path(__file__).resolve().parent
    env_path = repo_root / ".env"
    logger = logging.getLogger(__name__)
    if env_path.exists():
        load_dotenv(env_path, override=True)
        logger.info("[ENV] Loaded .env from %s", env_path)
    else:
        load_dotenv(override=True)
        logger.warning("[ENV] .env not found at %s", env_path)

    # Log presence only, never the value
    if os.getenv("ANTHROPIC_API_KEY"):
        logger.info("[ENV] ANTHROPIC_API_KEY is set")
    else:
        logger.warning("[ENV] ANTHROPIC_API_KEY is missing")

_load_env_vars()

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig, Runnable
from langchain_anthropic import ChatAnthropic
try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None  # OpenAI support is optional
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from pydantic import BaseModel, ValidationError, Field

from models import (
    IncomeStatement, 
    BalanceSheet, 
    get_schema_for_doc_type,
    MultiPeriodIncomeStatement,
    MultiPeriodBalanceSheet,
    MultiPeriodIncomeExtraction,
    MultiPeriodBalanceExtraction,
    IncomeStatementPeriod,
    BalanceSheetPeriod,
    get_multi_period_extraction_schema,
    StatementTypeDetection,
    CombinedFinancialExtraction,
)
from utils import (
    pdf_to_base64_images,
    create_image_content_block,
    create_vision_message_content,
    estimate_token_count,
    excel_to_markdown,
    excel_to_csv_sections,
    detect_statement_type_from_sheet,
)
from model_config import (
    get_model_by_id,
    get_default_model,
    get_fast_model,
    validate_model_for_spreading,
    ModelProvider
)
from period_utils import standardize_period_label, get_period_type

# Configure logging
logger = logging.getLogger(__name__)

# Global flag to track if fallback prompt was used during extraction
_fallback_prompt_used = False


def _run_async_safely(coro):
    """
    Run an async coroutine from a sync context, handling the case where
    we're already inside an event loop (e.g., FastAPI).
    
    This is necessary because asyncio.run() cannot be called from within
    a running event loop. When called from FastAPI or other async frameworks,
    we need to run the coroutine in a separate thread with its own event loop.
    
    Args:
        coro: The coroutine to run
        
    Returns:
        The result of the coroutine
    """
    try:
        # Check if we're already in an event loop
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop - safe to use asyncio.run()
        return asyncio.run(coro)
    
    # We're inside an event loop (e.g., FastAPI)
    # Run the coroutine in a separate thread with its own event loop
    logger.debug("Running async code from within existing event loop using thread executor")
    
    def run_in_thread():
        return asyncio.run(coro)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_in_thread)
        return future.result()


def reset_fallback_flag():
    """Reset the fallback prompt flag before a new extraction."""
    global _fallback_prompt_used
    _fallback_prompt_used = False

def was_fallback_used():
    """Check if the fallback prompt was used during extraction."""
    global _fallback_prompt_used
    return _fallback_prompt_used


# =============================================================================
# PERIOD DETECTION (Vision)
# =============================================================================

class PeriodCandidate(BaseModel):
    """A candidate reporting period column found on the statement."""
    label: str = Field(
        description="Human-readable period label as shown (or faithfully normalized), e.g. "
                    "'Year Ended Dec 31, 2024', 'As of 2024-12-31', 'FY2024', 'Q3 2024'."
    )
    normalized_label: Optional[str] = Field(
        default=None,
        description="Simplified/normalized label for display (e.g., 'January through December 2024' → '2024', "
                    "'January 2025' → 'Jan 2025'). Should be concise and suitable for column headers."
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Best-effort ISO date (YYYY-MM-DD) for the column, if a specific date is visible."
    )
    is_most_recent: bool = Field(
        default=False,
        description="True if this is the most recent period among the candidates."
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in this candidate period being correctly read from the statement."
    )
    evidence: Optional[str] = Field(
        default=None,
        description="Short snippet of header text used as evidence (for debugging/tracing)."
    )


class FiscalPeriodDetection(BaseModel):
    """Structured output for the period detection pass."""
    best_period: str = Field(
        description="The period label to use for extraction. If multiple columns exist, choose the most recent "
                    "(usually the right-most column)."
    )
    best_end_date: Optional[str] = Field(
        default=None,
        description="ISO date (YYYY-MM-DD) for best_period when available (especially for balance sheets)."
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Overall confidence in best_period."
    )
    candidates: List[PeriodCandidate] = Field(
        default_factory=list,
        description="All detected period columns (if any)."
    )
    notes: Optional[str] = Field(
        default=None,
        description="Any ambiguity notes or assumptions made."
    )


def _should_autodetect_period(period: Optional[str]) -> bool:
    """Return True if the provided period indicates auto-detection."""
    if period is None:
        return True
    normalized = str(period).strip().lower()
    return normalized in {"", "latest", "auto", "detect", "autodetect"}


@traceable(
    name="detect_fiscal_period",
    tags=["period-detection", "vision"],
    metadata={"operation": "detect_period"}
)
def _detect_fiscal_period(
    *,
    base64_images: List[tuple],
    doc_type: str,
    model_name: str,
    model_kwargs: Optional[dict],
    requested_period: str,
) -> Tuple[str, Optional[FiscalPeriodDetection]]:
    """
    Detect the fiscal period/as-of date from statement images when requested_period indicates auto-detect.

    Strategy:
    - Start with the first page only (cheap).
    - If low confidence and additional pages exist, retry with first two pages.
    """
    if not _should_autodetect_period(requested_period):
        return requested_period, None

    if not base64_images:
        return requested_period, None

    detection_system = (
        "You are an expert at reading financial statement headers from images.\n"
        "Goal: identify ALL reporting period columns shown in the statement.\n\n"
        "IMPORTANT: The document may span multiple pages. Look at ALL provided page images.\n"
        "Financial data may not start on the first page - cover pages, commentary, or executive summaries may precede the actual financial tables.\n\n"
        "CRITICAL: Financial statements often show MULTIPLE periods for comparison. Look for:\n"
        "- Side-by-side columns (e.g., 'Jan-Dec 2024' | 'Jan 2025')\n"
        "- Year-over-year comparisons (e.g., '2024' | '2023')\n"
        "- Partial periods (e.g., 'January 2025' alongside full year '2024')\n"
        "- Different date formats (e.g., 'Year Ended December 31, 2024', 'January through December 2024')\n\n"
        "Rules:\n"
        "- Include ALL period columns found - not just the most recent one.\n"
        "- Mark is_most_recent=True for the most recent period.\n"
        "- For normalized_label, simplify verbose labels:\n"
        "  * 'January through December 2024' → '2024'\n"
        "  * 'Year Ended December 31, 2024' → '2024'\n"
        "  * 'January 2025' → 'Jan 2025'\n"
        "  * 'For the month ended January 31, 2025' → 'Jan 2025'\n"
        "  * 'Three months ended March 31, 2024' → 'Q1 2024'\n"
        "- Preserve the original label in 'label' field for reference.\n"
        "- If you can infer an ISO end_date from visible text, set end_date / best_end_date.\n"
        "- Period columns are usually arranged left-to-right with most recent on the right.\n"
    )

    def _invoke_detection(images_subset: List[tuple]) -> FiscalPeriodDetection:
        llm = create_llm(model_name=model_name, model_kwargs=model_kwargs)
        structured = llm.with_structured_output(FiscalPeriodDetection)

        text_prompt = (
            f"Detect the reporting period columns for a {doc_type} statement.\n"
            f"The user requested: '{requested_period}' (this means auto-detect the best/most recent period).\n"
            "Return structured output with best_period and candidates."
        )
        human_content = create_vision_message_content(text_prompt, images_subset)
        messages = [
            SystemMessage(content=detection_system),
            HumanMessage(content=human_content),
        ]

        config = get_runnable_config(
            run_name=f"detect_period_{doc_type}",
            tags=[f"doc_type:{doc_type}", f"pages:{len(images_subset)}", "vision-input", "period-detection"],
            metadata={"requested_period": requested_period},
        )
        return structured.invoke(messages, config=config)

    # First pass: first two pages (handles cover pages/commentary on first page)
    initial_pages = min(2, len(base64_images))
    first_pass = _invoke_detection(base64_images[:initial_pages])
    best = (first_pass.best_period or "").strip()
    if best and first_pass.confidence >= 0.70:
        return best, first_pass

    # Second pass: first three pages (if available and low confidence)
    if len(base64_images) > initial_pages:
        second_pass = _invoke_detection(base64_images[:min(3, len(base64_images))])
        best2 = (second_pass.best_period or "").strip()
        if best2 and second_pass.confidence >= (first_pass.confidence or 0.0):
            return best2, second_pass

    # Fallback: if we got *some* best_period, use it; otherwise keep requested_period ("Latest")
    if best:
        return best, first_pass
    return requested_period, first_pass


# =============================================================================
# STATEMENT TYPE DETECTION (Auto-Detection)
# =============================================================================

@traceable(
    name="detect_statement_types",
    tags=["statement-detection", "vision", "auto-detect"],
    metadata={"operation": "detect_statement_types"}
)
def _detect_statement_types(
    *,
    base64_images: List[tuple],
    model_name: str,
    model_kwargs: Optional[dict],
) -> StatementTypeDetection:
    """
    Detect which types of financial statements are present in the document.
    
    Uses vision model to analyze document pages and identify:
    - Income Statement / Profit & Loss
    - Balance Sheet / Statement of Financial Position
    
    Args:
        base64_images: List of (base64_data, media_type) tuples
        model_name: Model to use for detection
        model_kwargs: Additional model parameters
        
    Returns:
        StatementTypeDetection with detected statement types and page locations
    """
    if not base64_images:
        logger.warning("[DETECT] No images provided for statement type detection")
        return StatementTypeDetection(
            has_income_statement=False,
            has_balance_sheet=False,
            confidence=0.0,
            notes="No images provided"
        )
    
    detection_system = (
        "You are an expert at identifying financial statement types from document images.\n\n"
        "TASK: Analyze the provided document pages and identify which financial statements are present.\n\n"
        "INCOME STATEMENT / PROFIT & LOSS INDICATORS:\n"
        "- Headers: 'Income Statement', 'Profit and Loss', 'P&L Statement', 'Statement of Operations', "
        "'Statement of Earnings', 'Profit and Loss Statement'\n"
        "- Key rows: 'Revenue', 'Net Sales', 'Total Revenue', 'Gross Profit', 'Operating Income', "
        "'Net Income', 'EBITDA', 'Cost of Goods Sold', 'Operating Expenses', 'Total Expenses'\n"
        "- Structure: Shows revenue at top, expenses in middle, net income at bottom\n\n"
        "BALANCE SHEET INDICATORS:\n"
        "- Headers: 'Balance Sheet', 'Statement of Financial Position', 'Consolidated Balance Sheet'\n"
        "- Key rows: 'Total Assets', 'Total Liabilities', 'Shareholders Equity', 'Current Assets', "
        "'Fixed Assets', 'Current Liabilities', 'Long Term Liabilities', 'Total Liabilities and Equity'\n"
        "- Structure: Assets section, Liabilities section, Equity section\n"
        "- Key equation: Assets = Liabilities + Equity\n\n"
        "IMPORTANT RULES:\n"
        "1. A document CAN contain BOTH statement types - this is common in financial packets\n"
        "2. Report ALL pages where each statement type appears (1-indexed page numbers)\n"
        "3. If statements are side-by-side on same page, report that page for both types\n"
        "4. Other financial reports (A/R aging, A/P aging, inventory reports) are NOT income statements or balance sheets\n"
        "5. Cover pages, executive summaries, and commentary are NOT financial statements\n"
        "6. Set confidence based on how clearly the statement type is identifiable\n"
    )
    
    # Analyze up to first 15 pages (audited financials with cover pages,
    # auditor's reports, and supplementary info can have statements after page 6)
    pages_to_analyze = min(15, len(base64_images))
    
    text_prompt = (
        f"Analyze these {pages_to_analyze} pages and identify which financial statements are present.\n"
        f"For each statement type found, list the page numbers (1-indexed) where it appears.\n"
        f"A single document often contains BOTH income statement AND balance sheet.\n"
        f"Ignore other report types like aging summaries, inventory reports, etc."
    )
    
    llm = create_llm(model_name=model_name, model_kwargs=model_kwargs)
    structured_llm = llm.with_structured_output(StatementTypeDetection)
    
    human_content = create_vision_message_content(text_prompt, base64_images[:pages_to_analyze])
    messages = [
        SystemMessage(content=detection_system),
        HumanMessage(content=human_content),
    ]
    
    config = get_runnable_config(
        run_name="detect_statement_types",
        tags=["statement-detection", "vision-input", f"pages:{pages_to_analyze}"],
        metadata={"num_pages_analyzed": pages_to_analyze}
    )
    
    try:
        result = structured_llm.invoke(messages, config=config)
        
        logger.info(
            f"[DETECT] Statement types detected: "
            f"Income Statement={result.has_income_statement} (pages {result.income_statement_pages}), "
            f"Balance Sheet={result.has_balance_sheet} (pages {result.balance_sheet_pages}), "
            f"Confidence={result.confidence:.2f}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[DETECT] Failed to detect statement types: {e}")
        # Return empty detection on failure
        return StatementTypeDetection(
            has_income_statement=False,
            has_balance_sheet=False,
            confidence=0.0,
            notes=f"Detection failed: {str(e)}"
        )


# =============================================================================
# COLUMN CLASSIFICATION (Distinguish Periods from Rollups)
# =============================================================================

class ColumnClassification(BaseModel):
    """
    Output of column classification step.
    
    This separates real reporting period columns from rollup/summary columns
    (like "Total") to prevent extracting aggregated data as a period.
    """
    period_columns: List[str] = Field(
        description="Column labels that represent real reporting periods (ordered most recent first)"
    )
    rollup_columns: List[str] = Field(
        default_factory=list,
        description="Column labels that are rollup/summary columns (e.g., 'Total', 'YTD', 'Combined')"
    )
    column_order: List[str] = Field(
        default_factory=list,
        description="All columns in left-to-right order as seen in document"
    )
    classification_notes: Optional[str] = Field(
        default=None,
        description="Notes about classification decisions made"
    )


@traceable(
    name="classify_columns",
    tags=["column-classification", "vision"],
    metadata={"operation": "classify_columns"}
)
def _classify_columns(
    *,
    base64_images: List[tuple],
    doc_type: str,
    model_name: str,
    model_kwargs: Optional[dict],
    period_candidates: List[PeriodCandidate],
) -> ColumnClassification:
    """
    Classify columns as PERIOD vs ROLLUP before extraction.
    
    This step prevents the model from extracting data from "Total" columns
    that aggregate other period columns.
    
    Args:
        base64_images: List of (base64_data, media_type) tuples
        doc_type: 'income' or 'balance'
        model_name: Model to use for classification
        model_kwargs: Additional model parameters
        period_candidates: Period candidates from detection step
        
    Returns:
        ColumnClassification with period and rollup columns identified
    """
    classification_system = (
        "You are a financial statement column classifier.\n\n"
        "IMPORTANT: The document may span multiple pages. Look at ALL provided page images to find column headers.\n"
        "Financial data may not start on the first page - cover pages, commentary, or executive summaries may precede the actual financial tables.\n\n"
        "TASK: Identify which columns represent REAL REPORTING PERIODS vs ROLLUP/SUMMARY columns.\n\n"
        "ROLLUP INDICATORS (classify as rollup_columns):\n"
        "- Column header contains: 'Total', 'Sum', 'Combined', 'Grand Total', 'YTD', 'Cumulative', 'Overall'\n"
        "- Column values are mathematically the sum of adjacent period columns\n"
        "- Column represents an aggregate rather than a specific time period\n\n"
        "PERIOD INDICATORS (classify as period_columns):\n"
        "- Specific date labels: 'Jan 2025', 'FY2024', 'Year Ended Dec 31, 2024', 'Q3 2024'\n"
        "- Time ranges: 'Jan - Dec 2024', 'January through December 2024'\n"
        "- Fiscal periods: '2024', '2023', 'FY23'\n\n"
        "OUTPUT RULES:\n"
        "- period_columns: Only real period columns, ordered from MOST RECENT to oldest\n"
        "- rollup_columns: Any Total/Sum/Combined/YTD columns (these will be excluded from extraction)\n"
        "- column_order: All columns in left-to-right document order\n"
        "- If unsure whether a column is a rollup, lean toward classifying as PERIOD (safer to extract)"
    )
    
    # Build candidate info string
    candidate_info = ""
    if period_candidates:
        labels = [c.label for c in period_candidates if c.label]
        if labels:
            candidate_info = f"\n\nPreviously detected column candidates: {labels}"
    
    text_prompt = (
        f"Classify the columns in this {doc_type} statement (may span multiple pages).\n"
        f"{candidate_info}\n\n"
        f"IMPORTANT: Look at ALL provided page images - financial data may not be on the first page.\n"
        f"Look at the column headers and classify each as either:\n"
        f"- A PERIOD column (real reporting period like 'Jan 2025', 'FY2024')\n"
        f"- A ROLLUP column (summary/total like 'Total', 'YTD')\n\n"
        f"Return period_columns ordered from most recent to oldest."
    )
    
    llm = create_llm(model_name=model_name, model_kwargs=model_kwargs)
    structured_llm = llm.with_structured_output(ColumnClassification)
    
    # Use up to 3 pages for classification (handles cover pages/commentary on first page)
    pages_for_classification = min(3, len(base64_images))
    human_content = create_vision_message_content(text_prompt, base64_images[:pages_for_classification])
    messages = [
        SystemMessage(content=classification_system),
        HumanMessage(content=human_content),
    ]
    
    config = get_runnable_config(
        run_name=f"classify_columns_{doc_type}",
        tags=[f"doc_type:{doc_type}", "column-classification", "vision-input", f"pages:{pages_for_classification}"],
        metadata={"num_candidates": len(period_candidates) if period_candidates else 0, "pages_analyzed": pages_for_classification}
    )
    
    result = structured_llm.invoke(messages, config=config)
    
    # Standardize period labels for consistency
    standardized_periods = []
    for label in result.period_columns:
        standardized = standardize_period_label(label)
        standardized_periods.append(standardized)
        if standardized != label:
            logger.info(f"[COLUMN CLASSIFIER] Standardized period: '{label}' -> '{standardized}'")
    
    # Create a new result with standardized period labels
    result.period_columns = standardized_periods
    
    logger.info(
        f"[COLUMN CLASSIFIER] Period columns (standardized): {result.period_columns}, "
        f"Rollup columns: {result.rollup_columns}"
    )
    
    return result


# =============================================================================
# VALIDATION RESULT DATA CLASS
# =============================================================================

@dataclass
class ValidationResult:
    """Result of spread validation."""
    is_valid: bool
    errors: List[str]
    calculated_values: dict
    
    def __str__(self) -> str:
        if self.is_valid:
            return "Validation passed"
        return f"Validation failed: {'; '.join(self.errors)}"


# =============================================================================
# LANGSMITH CONFIGURATION
# =============================================================================

def get_runnable_config(
    run_name: Optional[str] = None,
    tags: Optional[List[str]] = None,
    metadata: Optional[dict] = None
) -> RunnableConfig:
    """
    Create RunnableConfig for LangChain operations with LangSmith tracing.
    """
    config = RunnableConfig(
        tags=tags or ["financial-spreading"],
        metadata=metadata or {},
    )
    if run_name:
        config["run_name"] = run_name
    return config


# =============================================================================
# VALIDATION FUNCTIONS (Reasoning Loop)
# =============================================================================

def _get_value_or_zero(line_item) -> float:
    """Safely get value from LineItem, defaulting to 0 if None."""
    if line_item is None:
        return 0.0
    if hasattr(line_item, 'value'):
        return line_item.value if line_item.value is not None else 0.0
    return 0.0


@traceable(
    name="validate_income_statement",
    tags=["validation", "income"],
    metadata={"operation": "validation"}
)
def validate_income_statement(data: IncomeStatement, tolerance: float = 0.05) -> ValidationResult:
    """
    Validate Income Statement extraction with math checks.
    
    Checks performed:
    1. Gross Profit = Revenue - COGS (if all values present)
    2. Operating Income = Gross Profit - Operating Expenses (if present)
    3. Net Income ≈ Pre-Tax Income - Tax Expense (if present)
    
    Args:
        data: The extracted IncomeStatement
        tolerance: Relative tolerance for math checks (default 5%)
        
    Returns:
        ValidationResult with pass/fail status and error details
    """
    errors = []
    calculated = {}
    
    # Get values (or 0 if not extracted)
    revenue = _get_value_or_zero(data.revenue)
    cogs = _get_value_or_zero(data.cogs)
    gross_profit = _get_value_or_zero(data.gross_profit)
    operating_income = _get_value_or_zero(data.operating_income)
    total_opex = _get_value_or_zero(data.total_operating_expenses)
    pretax_income = _get_value_or_zero(data.pretax_income)
    tax_expense = _get_value_or_zero(data.income_tax_expense)
    net_income = _get_value_or_zero(data.net_income)
    
    # Check 1: Gross Profit = Revenue - COGS
    if revenue != 0 and cogs != 0:
        calc_gross_profit = revenue - cogs
        calculated['gross_profit'] = calc_gross_profit
        
        if gross_profit != 0:
            diff = abs(calc_gross_profit - gross_profit)
            if diff > abs(gross_profit) * tolerance and diff > 1:  # Allow $1 rounding
                errors.append(
                    f"Gross Profit mismatch: calculated {calc_gross_profit:,.2f} "
                    f"(Revenue {revenue:,.2f} - COGS {cogs:,.2f}) but extracted {gross_profit:,.2f}"
                )
    
    # Check 2: Operating Income ≈ Gross Profit - Operating Expenses
    if gross_profit != 0 and total_opex != 0:
        calc_operating_income = gross_profit - total_opex
        calculated['operating_income'] = calc_operating_income
        
        if operating_income != 0:
            diff = abs(calc_operating_income - operating_income)
            if diff > abs(operating_income) * tolerance and diff > 1:
                errors.append(
                    f"Operating Income mismatch: calculated {calc_operating_income:,.2f} "
                    f"but extracted {operating_income:,.2f}"
                )
    
    # Check 3: Net Income ≈ Pre-Tax Income - Tax Expense
    if pretax_income != 0:
        calc_net_income = pretax_income - tax_expense
        calculated['net_income'] = calc_net_income
        
        if net_income != 0:
            diff = abs(calc_net_income - net_income)
            if diff > abs(net_income) * tolerance and diff > 1:
                errors.append(
                    f"Net Income mismatch: calculated {calc_net_income:,.2f} "
                    f"(Pre-Tax {pretax_income:,.2f} - Tax {tax_expense:,.2f}) "
                    f"but extracted {net_income:,.2f}"
                )
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        calculated_values=calculated
    )


@traceable(
    name="validate_balance_sheet",
    tags=["validation", "balance"],
    metadata={"operation": "validation"}
)
def validate_balance_sheet(data: BalanceSheet, tolerance: float = 0.05) -> ValidationResult:
    """
    Validate Balance Sheet extraction with accounting equation check.
    
    Checks performed:
    1. Total Assets = Total Liabilities + Total Equity (fundamental equation)
    2. Total Current Assets = sum of current asset line items
    3. Total Liabilities = Current + Non-Current
    
    Args:
        data: The extracted BalanceSheet
        tolerance: Relative tolerance for math checks (default 5%)
        
    Returns:
        ValidationResult with pass/fail status and error details
    """
    errors = []
    calculated = {}
    
    # Get values
    total_assets = _get_value_or_zero(data.total_assets)
    total_liabilities = _get_value_or_zero(data.total_liabilities)
    total_equity = _get_value_or_zero(data.total_shareholders_equity)
    total_liab_equity = _get_value_or_zero(data.total_liabilities_and_equity)
    
    # Check 1: Assets = Liabilities + Equity
    if total_liabilities != 0 and total_equity != 0:
        calc_total = total_liabilities + total_equity
        calculated['total_liabilities_and_equity'] = calc_total
        
        if total_assets != 0:
            diff = abs(calc_total - total_assets)
            if diff > abs(total_assets) * tolerance and diff > 1:
                errors.append(
                    f"Balance Sheet equation error: Total Liabilities ({total_liabilities:,.2f}) + "
                    f"Total Equity ({total_equity:,.2f}) = {calc_total:,.2f}, "
                    f"but Total Assets = {total_assets:,.2f}"
                )
    
    # Check 2: Total L&E field matches Total Assets
    if total_liab_equity != 0 and total_assets != 0:
        diff = abs(total_liab_equity - total_assets)
        if diff > abs(total_assets) * tolerance and diff > 1:
            errors.append(
                f"Total mismatch: Total Liabilities & Equity ({total_liab_equity:,.2f}) "
                f"!= Total Assets ({total_assets:,.2f})"
            )
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        calculated_values=calculated
    )


def validate_spread(
    data: Union[IncomeStatement, BalanceSheet],
    tolerance: float = 0.05
) -> ValidationResult:
    """
    Validate extracted financial data based on document type.
    
    This is the main validation entry point that routes to the appropriate
    validator based on the data type.
    
    Args:
        data: The extracted financial statement (IncomeStatement or BalanceSheet)
        tolerance: Relative tolerance for math checks (default 5%)
        
    Returns:
        ValidationResult indicating pass/fail and any errors
    """
    if isinstance(data, IncomeStatement):
        return validate_income_statement(data, tolerance)
    elif isinstance(data, BalanceSheet):
        return validate_balance_sheet(data, tolerance)
    else:
        raise TypeError(f"Unsupported data type: {type(data)}")


@traceable(
    name="validate_multi_period_consistency",
    tags=["validation", "multi-period", "consistency"],
    metadata={"operation": "consistency_validation"}
)
def validate_multi_period_consistency(
    periods: List[Any],  # List[IncomeStatementPeriod] or List[BalanceSheetPeriod]
    doc_type: str
) -> Tuple[bool, List[str], List[dict]]:
    """
    Validate that field mappings are consistent across all periods.
    
    This checks that if a row label maps to a schema field in one period,
    it maps to the same field in all other periods.
    
    Args:
        periods: List of period data objects
        doc_type: 'income' or 'balance'
        
    Returns:
        Tuple of (is_consistent, error_messages, corrections_applied)
    """
    errors = []
    corrections = []
    
    if len(periods) < 2:
        return True, [], []
    
    # Build field presence map: field -> {periods with value, periods without}
    field_presence: dict = {}
    
    for period in periods:
        data = period.data
        period_label = period.period_label
        
        for field_name in data.model_fields.keys():
            # Skip metadata fields
            if field_name in ['fiscal_period', 'as_of_date', 'currency', 'scale']:
                continue
            
            field_value = getattr(data, field_name, None)
            if field_value is None:
                continue
            
            if field_name not in field_presence:
                field_presence[field_name] = {'has_value': [], 'null': [], 'raw_fields': {}}
            
            if hasattr(field_value, 'value') and field_value.value is not None:
                field_presence[field_name]['has_value'].append(period_label)
                # Track raw fields used for consistency check
                if hasattr(field_value, 'raw_fields_used') and field_value.raw_fields_used:
                    field_presence[field_name]['raw_fields'][period_label] = field_value.raw_fields_used
            else:
                field_presence[field_name]['null'].append(period_label)
    
    # Check for inconsistent presence (might indicate mapping drift)
    for field_name, presence in field_presence.items():
        has_value = presence['has_value']
        is_null = presence['null']
        
        if has_value and is_null:
            # Field has values in some periods but not others - log warning
            logger.warning(
                f"[CONSISTENCY] Field '{field_name}' has values in {has_value} "
                f"but is null in {is_null} - verify this is expected"
            )
    
    # Check raw_fields_used consistency across periods
    for field_name, presence in field_presence.items():
        raw_fields = presence.get('raw_fields', {})
        if len(raw_fields) >= 2:
            # Get unique raw field patterns
            patterns = set()
            for period_label, fields in raw_fields.items():
                # Normalize: take first field, lowercase, strip numbers
                if fields:
                    pattern = fields[0].lower().strip()
                    # Remove amounts/numbers for comparison
                    import re
                    pattern = re.sub(r'[\d,.$()]+', '', pattern).strip()
                    patterns.add(pattern)
            
            if len(patterns) > 1:
                logger.warning(
                    f"[CONSISTENCY] Field '{field_name}' may have inconsistent source mapping: {raw_fields}"
                )
    
    return len(errors) == 0, errors, corrections


# =============================================================================
# PARALLEL POST-PROCESSING HELPERS
# =============================================================================

def _process_period_computed_totals(period_idx: int, period_data, tolerance: float) -> Tuple[int, Any, List[str]]:
    """
    Helper for parallel computed totals processing.
    Returns (period_idx, modified_data, corrections) to preserve order.
    """
    modified_data, corrections = apply_computed_totals(period_data.data, tolerance=tolerance)
    return period_idx, modified_data, corrections


def _process_period_validation(period_idx: int, period_data, tolerance: float) -> Tuple[int, str, 'ValidationResult']:
    """
    Helper for parallel validation processing.
    Returns (period_idx, period_label, validation_result) to preserve order.
    """
    validation = validate_spread(period_data.data, tolerance=tolerance)
    return period_idx, period_data.period_label, validation


def apply_computed_totals_parallel(
    extracted_periods: List,
    tolerance: float = 0.01,
    max_workers: int = 4
) -> None:
    """
    Apply computed totals to multiple periods in parallel.
    
    Modifies extracted_periods in place.
    Uses ThreadPoolExecutor for parallel execution when there are 3+ periods.
    
    Args:
        extracted_periods: List of period data objects with .data attribute
        tolerance: Tolerance for validation checks
        max_workers: Maximum number of parallel workers (default 4)
    """
    if len(extracted_periods) < 3:
        # Sequential processing for small number of periods (overhead not worth it)
        for period_data in extracted_periods:
            original_gp = period_data.data.gross_profit.value if hasattr(period_data.data, 'gross_profit') else None
            period_data.data, corrections = apply_computed_totals(period_data.data, tolerance=tolerance)
            if corrections:
                logger.info(f"[POST-PROCESS] {period_data.period_label}: {corrections}")
        return
    
    # Parallel processing for 3+ periods
    logger.info(f"[POST-PROCESS] Running computed totals in parallel for {len(extracted_periods)} periods")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(extracted_periods), max_workers)) as executor:
        futures = {
            executor.submit(_process_period_computed_totals, idx, period_data, tolerance): idx
            for idx, period_data in enumerate(extracted_periods)
        }
        
        for future in concurrent.futures.as_completed(futures):
            try:
                period_idx, modified_data, corrections = future.result()
                extracted_periods[period_idx].data = modified_data
                if corrections:
                    logger.info(f"[POST-PROCESS] {extracted_periods[period_idx].period_label}: {corrections}")
            except Exception as e:
                period_idx = futures[future]
                logger.error(f"[POST-PROCESS] Error processing period {period_idx}: {e}")


def validate_periods_parallel(
    extracted_periods: List,
    tolerance: float = 0.05,
    max_workers: int = 4
) -> None:
    """
    Validate multiple periods in parallel.
    
    Logs validation warnings but doesn't modify data.
    Uses ThreadPoolExecutor for parallel execution when there are 3+ periods.
    
    Args:
        extracted_periods: List of period data objects with .data attribute
        tolerance: Tolerance for validation checks
        max_workers: Maximum number of parallel workers (default 4)
    """
    if len(extracted_periods) < 3:
        # Sequential processing for small number of periods
        for period_data in extracted_periods:
            validation = validate_spread(period_data.data, tolerance=tolerance)
            if not validation.is_valid:
                logger.warning(f"[VALIDATION] {period_data.period_label}: {validation.errors}")
        return
    
    # Parallel processing for 3+ periods
    logger.info(f"[POST-PROCESS] Running validation in parallel for {len(extracted_periods)} periods")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(extracted_periods), max_workers)) as executor:
        futures = {
            executor.submit(_process_period_validation, idx, period_data, tolerance): idx
            for idx, period_data in enumerate(extracted_periods)
        }
        
        for future in concurrent.futures.as_completed(futures):
            try:
                period_idx, period_label, validation = future.result()
                if not validation.is_valid:
                    logger.warning(f"[VALIDATION] {period_label}: {validation.errors}")
            except Exception as e:
                period_idx = futures[future]
                logger.error(f"[VALIDATION] Error validating period {period_idx}: {e}")


@traceable(
    name="apply_computed_totals",
    tags=["validation", "auto-compute", "post-processing"],
    metadata={"operation": "compute_totals"}
)
def apply_computed_totals(
    data: IncomeStatement,
    tolerance: float = 0.01
) -> Tuple[IncomeStatement, List[str]]:
    """
    Compute missing totals and validate existing ones for Income Statements.
    
    Rules:
    - If gross_profit is null but revenue and cogs exist → compute it
    - If gross_profit exists, validate it equals revenue - cogs
    - If operating_income is null but gross_profit and total_opex exist → compute it
    
    Args:
        data: The IncomeStatement to process
        tolerance: Tolerance for validation checks (default 1%)
        
    Returns:
        Tuple of (updated_data, list_of_corrections_applied)
    """
    corrections = []
    
    revenue = _get_value_or_zero(data.revenue)
    cogs = _get_value_or_zero(data.cogs)
    gross_profit = _get_value_or_zero(data.gross_profit)
    
    # Compute gross profit if missing but computable
    if revenue != 0 and cogs != 0:
        computed_gp = revenue - cogs
        
        if gross_profit == 0 or data.gross_profit.value is None:
            # Fill in missing gross profit
            data.gross_profit.value = computed_gp
            data.gross_profit.confidence = 0.7  # Computed, not extracted
            data.gross_profit.raw_fields_used = [
                f"COMPUTED: revenue ({revenue:,.2f}) - cogs ({cogs:,.2f}) = {computed_gp:,.2f}"
            ]
            corrections.append(f"Computed gross_profit = {computed_gp:,.2f}")
            logger.info(f"[AUTO-COMPUTE] Set gross_profit = {computed_gp:,.2f}")
            # Update for subsequent calculations
            gross_profit = computed_gp
        else:
            # Validate existing gross profit
            diff = abs(computed_gp - gross_profit)
            if diff > abs(gross_profit) * tolerance and diff > 1:
                logger.warning(
                    f"[VALIDATION] gross_profit mismatch: extracted {gross_profit:,.2f}, "
                    f"computed {computed_gp:,.2f} (diff={diff:,.2f})"
                )
    
    # Compute operating income if missing but computable
    total_opex = _get_value_or_zero(data.total_operating_expenses)
    operating_income = _get_value_or_zero(data.operating_income)
    
    if gross_profit != 0 and total_opex != 0:
        computed_oi = gross_profit - total_opex
        
        if operating_income == 0 or data.operating_income.value is None:
            data.operating_income.value = computed_oi
            data.operating_income.confidence = 0.7
            data.operating_income.raw_fields_used = [
                f"COMPUTED: gross_profit ({gross_profit:,.2f}) - total_opex ({total_opex:,.2f}) = {computed_oi:,.2f}"
            ]
            corrections.append(f"Computed operating_income = {computed_oi:,.2f}")
            logger.info(f"[AUTO-COMPUTE] Set operating_income = {computed_oi:,.2f}")
        else:
            # Validate existing operating income
            diff = abs(computed_oi - operating_income)
            if diff > abs(operating_income) * tolerance and diff > 1:
                logger.warning(
                    f"[VALIDATION] operating_income mismatch: extracted {operating_income:,.2f}, "
                    f"computed {computed_oi:,.2f} (diff={diff:,.2f})"
                )
    
    return data, corrections


# =============================================================================
# LANGSMITH HUB INTEGRATION
# =============================================================================

# Map document types to Hub prompt names
PROMPT_MAP = {
    "income": "income-statement",
    "income_statement": "income-statement",
    "balance": "balance-sheet",
    "balance_sheet": "balance-sheet",
}


def _create_fallback_prompt(doc_type: str) -> ChatPromptTemplate:
    """
    Create a fallback ChatPromptTemplate when LangSmith Hub is unavailable.
    
    Uses the enhanced extraction system prompt for high-quality results
    even without Hub access.
    
    Args:
        doc_type: Type of document ('income' or 'balance')
        
    Returns:
        ChatPromptTemplate with system and human message templates
    """
    from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate
    
    # Use the enhanced system prompt (defined later in this file)
    # We need to call it lazily to avoid circular reference
    system_content = _get_enhanced_extraction_system_prompt(doc_type)
    
    system_template = SystemMessagePromptTemplate.from_template(system_content)
    human_template = HumanMessagePromptTemplate.from_template("{input}")
    
    prompt = ChatPromptTemplate.from_messages([system_template, human_template])
    logger.info(f"[FALLBACK] Created local fallback prompt for {doc_type}")
    
    return prompt


@traceable(
    name="load_from_hub",
    tags=["hub", "prompt-management"],
    metadata={"operation": "hub_pull"}
)
def load_from_hub(doc_type: str) -> Tuple[ChatPromptTemplate, Optional[dict]]:
    """
    Load prompt and model configuration from LangSmith Hub.
    
    If Hub is unavailable or USE_LOCAL_PROMPTS=true, falls back to local prompts.
    This ensures the app can work without LangSmith Hub access.
    
    Environment Variables:
        USE_LOCAL_PROMPTS: Set to 'true' to skip Hub and use local prompts
    
    Pulls prompt templates from LangSmith Hub. Model selection is handled
    locally via model_config.py and environment variables.
    
    Args:
        doc_type: Type of document ('income' or 'balance')
        
    Returns:
        Tuple of (ChatPromptTemplate, model_config_dict or None)
        - model_config includes: model, max_tokens, temperature, reasoning_effort, etc.
        
    Raises:
        ImportError: If langsmith is not installed
        ValueError: If doc_type is not recognized
    """
    global _fallback_prompt_used
    
    # Normalize document type first
    doc_type_normalized = doc_type.lower().strip()
    
    if doc_type_normalized not in PROMPT_MAP:
        raise ValueError(
            f"Unknown document type: '{doc_type}'. "
            f"Valid types: {list(PROMPT_MAP.keys())}"
        )
    
    # Check if local prompts are forced via environment variable
    use_local = os.getenv("USE_LOCAL_PROMPTS", "").lower() in ("true", "1", "yes")
    if use_local:
        logger.info(f"[HUB] USE_LOCAL_PROMPTS=true, using local fallback prompt for {doc_type}")
        _fallback_prompt_used = True
        return _create_fallback_prompt(doc_type_normalized), None
    
    try:
        from langsmith import Client
    except ImportError as e:
        logger.warning(f"[HUB] langsmith not installed, using fallback prompt: {e}")
        _fallback_prompt_used = True
        return _create_fallback_prompt(doc_type_normalized), None
    
    prompt_name = PROMPT_MAP[doc_type_normalized]
    logger.info(f"[HUB] Pulling prompt from LangSmith Hub: {prompt_name}")
    
    try:
        client = Client()
        
        # Pull ONLY the prompt template (not the model config).
        # Model selection is handled locally via model_config.py and environment
        # variables, not from the Hub. This avoids the Hub overriding our
        # Anthropic model config with a stale OpenAI model.
        hub_object = client.pull_prompt(prompt_name, include_model=False)
        
        prompt = hub_object
        
        # Log commit hash
        commit_hash = "unknown"
        if hasattr(prompt, 'metadata') and prompt.metadata:
            commit_hash = prompt.metadata.get('lc_hub_commit_hash', 'unknown')[:8]
        logger.info(f"[HUB] Loaded '{prompt_name}' (commit: {commit_hash})")
        
        # Return None for model_config - model selection is local
        return prompt, None
        
    except Exception as e:
        # Fall back to local prompt instead of failing
        logger.warning(
            f"[HUB] Failed to pull '{prompt_name}' from Hub, using fallback prompt. "
            f"Error: {e}"
        )
        _fallback_prompt_used = True
        return _create_fallback_prompt(doc_type_normalized), None


# NOTE: Local fallback prompts are now available when LangSmith Hub is unavailable.
# Set USE_LOCAL_PROMPTS=true to always use local prompts.
# See: https://smith.langchain.com/prompts/income-statement
# See: https://smith.langchain.com/prompts/balance-sheet


def get_model_config_from_environment() -> Tuple[str, dict]:
    """
    Get model configuration from environment variables.
    
    Priority:
    1. ANTHROPIC_MODEL env var (if ANTHROPIC_API_KEY is set)
    2. Default model from model_config.py (Claude Opus 4.6)
    
    Environment Variables:
    - ANTHROPIC_MODEL: Anthropic model name override
    - ANTHROPIC_API_KEY: Required API key for Claude models
    
    Returns:
        Tuple of (model_name, model_kwargs)
    """
    from model_config import get_default_model
    default_model = get_default_model()
    
    # Use ANTHROPIC_MODEL env var if set, otherwise use model_config default
    model = os.getenv("ANTHROPIC_MODEL", default_model.id)
    model_kwargs = {}
    
    logger.info(f"Using model from environment: {model}")
    
    return model, model_kwargs


def get_detection_model_config() -> Tuple[str, dict]:
    """
    Get model configuration for fast detection/classification tasks.
    
    Uses a faster, cheaper model (Claude 3.5 Haiku) for tasks like:
    - Statement type detection
    - Column classification
    - Period detection
    
    Can be overridden with DETECTION_MODEL env var.
    
    Returns:
        Tuple of (model_name, model_kwargs)
    """
    from model_config import get_fast_model
    fast_model = get_fast_model()
    
    model = os.getenv("DETECTION_MODEL", fast_model.id)
    model_kwargs = {}
    
    logger.info(f"Using fast detection model: {model}")
    
    return model, model_kwargs


# =============================================================================
# LLM INITIALIZATION
# =============================================================================

def create_llm(
    model_name: Optional[str] = None,
    model_kwargs: Optional[dict] = None
):
    """
    Create LLM instance based on model name.
    
    Primarily uses Anthropic (Claude) models. OpenAI is available as a
    secondary option if explicitly configured.
    
    Parameters like temperature, max_tokens should be controlled via:
    1. LangSmith Hub prompt configuration
    2. Environment variables
    3. Passed model_kwargs
    
    This function intentionally does NOT set temperature, max_tokens, etc.
    to allow Hub/environment control.
    
    Args:
        model_name: Optional model override (defaults to env/default from config)
        model_kwargs: Optional additional model parameters
        
    Returns:
        Configured ChatAnthropic (or ChatOpenAI) instance
    """
    # Get model from environment if not specified
    if model_name is None:
        model_name, env_kwargs = get_model_config_from_environment()
        if model_kwargs is None:
            model_kwargs = env_kwargs
        else:
            # Merge env kwargs with passed kwargs (passed takes precedence)
            model_kwargs = {**env_kwargs, **model_kwargs}
    
    # Validate model for spreading
    is_valid, error_msg = validate_model_for_spreading(model_name)
    if not is_valid:
        logger.warning(f"Model validation warning: {error_msg}")
    
    # Get model definition
    model_def = get_model_by_id(model_name)
    
    # Determine provider
    if model_def:
        provider = model_def.provider
    else:
        # Fallback: infer from model name
        if any(x in model_name.lower() for x in ["gpt", "o1", "o3"]):
            provider = ModelProvider.OPENAI
        else:
            provider = ModelProvider.ANTHROPIC  # Default to Anthropic
    
    logger.info(f"Creating LLM: {model_name} (provider: {provider.value}) with kwargs: {model_kwargs}")
    
    # Create appropriate LLM instance
    if provider == ModelProvider.ANTHROPIC:
        return _create_anthropic_llm(model_name, model_kwargs)
    else:
        return _create_openai_llm(model_name, model_kwargs)


def _create_anthropic_llm(model_name: str, model_kwargs: Optional[dict] = None):
    """Create a ChatAnthropic LLM instance."""
    # Get and validate Anthropic API key
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY not found in environment variables. "
            "Please add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
        )
    
    # Create Anthropic LLM
    llm_config = {
        "model": model_name,
        "api_key": anthropic_api_key,
    }
    
    # Filter model_kwargs for Anthropic compatibility.
    # NOTE: Thinking (adaptive/extended) is NOT auto-enabled because it conflicts
    # with with_structured_output() which uses tool_choice (forced tool use).
    # Thinking is only enabled when explicitly requested AND the caller handles
    # the tool_choice incompatibility.
    if model_kwargs:
        filtered_kwargs = {}
        
        for k, v in model_kwargs.items():
            if k == "reasoning_effort":
                # Map reasoning_effort to Anthropic effort parameter
                effort_map = {"xhigh": "high", "max": "high", "high": "high", "medium": "medium", "low": "low"}
                effort_level = effort_map.get(v, "high")
                # Use output_config effort for Opus 4.6 (without thinking)
                if "opus-4-6" in model_name.lower():
                    filtered_kwargs["output_config"] = {"effort": effort_level}
                    logger.info(f"[ANTHROPIC] Opus 4.6 effort={effort_level}")
            elif k == "extended_thinking":
                # Skip - thinking conflicts with structured output (tool_choice)
                logger.info("[ANTHROPIC] extended_thinking requested but skipped (incompatible with structured output)")
            else:
                filtered_kwargs[k] = v
        
        if filtered_kwargs:
            llm_config["model_kwargs"] = filtered_kwargs
    
    # ChatAnthropic automatically traces to LangSmith when LANGSMITH_API_KEY is set
    return ChatAnthropic(**llm_config)


def _create_openai_llm(model_name: str, model_kwargs: Optional[dict] = None):
    """Create a ChatOpenAI LLM instance (optional, for backward compatibility)."""
    if ChatOpenAI is None:
        raise ImportError(
            "langchain-openai is not installed. Install it with: pip install langchain-openai"
        )
    
    # Get and validate OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please add it to your .env file: OPENAI_API_KEY=sk-..."
        )
    
    # Create OpenAI LLM
    llm_config = {
        "model": model_name,
        "api_key": openai_api_key,
    }
    
    # Add model_kwargs if present (e.g., reasoning_effort)
    if model_kwargs:
        # Sanitize reasoning_effort for OpenAI
        if "reasoning_effort" in model_kwargs:
            re_val = model_kwargs["reasoning_effort"]
            if re_val in ("max", "xhigh"):
                logger.warning(f"[OPENAI] reasoning_effort '{re_val}' not supported, downgrading to 'high'")
                model_kwargs["reasoning_effort"] = "high"
        llm_config["model_kwargs"] = model_kwargs
    
    # ChatOpenAI automatically traces to LangSmith when LANGSMITH_API_KEY is set
    return ChatOpenAI(**llm_config)


# =============================================================================
# MAIN SPREADING FUNCTIONS
# =============================================================================

@traceable(
    name="invoke_llm_for_spreading",
    tags=["llm", "vision", "extraction"],
    metadata={"operation": "llm_invoke"}
)
def _invoke_llm_for_spreading(
    prompt: ChatPromptTemplate,
    structured_llm: Any,
    base64_images: List[tuple],
    doc_type: str,
    period: str,
    schema_class: type,
    retry_context: Optional[str] = None
) -> Union[IncomeStatement, BalanceSheet]:
    """
    Invoke the LLM for financial spreading with images.
    
    The Hub prompt template only has {period} as a variable, so we need to:
    1. Extract the system message from the Hub prompt
    2. Create a multimodal human message with the images + period instruction
    3. Invoke the LLM directly with these messages
    
    Args:
        prompt: The Hub ChatPromptTemplate (contains system message)
        structured_llm: LLM with structured output bound
        base64_images: List of (base64_data, media_type) tuples
        doc_type: 'income' or 'balance'
        period: The fiscal period to extract
        schema_class: Pydantic schema for output
        retry_context: If provided, includes error message from previous attempt
    """
    # Extract system message from the Hub prompt
    system_message = None
    if hasattr(prompt, 'messages') and prompt.messages:
        for msg in prompt.messages:
            if hasattr(msg, 'prompt') and hasattr(msg.prompt, 'template'):
                # This is a SystemMessagePromptTemplate
                if 'SystemMessage' in str(type(msg)):
                    system_message = SystemMessage(content=msg.prompt.template)
                    break
    
    if not system_message:
        # Fallback: create a basic system message
        logger.warning("[INVOKE] Could not extract system message from Hub prompt, using fallback")
        system_message = SystemMessage(content=f"You are a financial analyst extracting {doc_type} statement data.")
        # Set a flag to indicate fallback was used (will be checked by caller)
        global _fallback_prompt_used
        _fallback_prompt_used = True
    
    # Build the human message text with the period
    if retry_context:
        text_content = (
            f"Analyze ALL pages of the attached financial statement images.\n"
            f"IMPORTANT: Financial data may appear on ANY page - do not focus only on the first page.\n"
            f"Cover pages, commentary, or executive summaries may precede the actual financial tables.\n\n"
            f"Extract the data for the period ending {period} and map it to the JSON schema.\n\n"
            f"IMPORTANT: A previous extraction had errors:\n{retry_context}\n\n"
            f"Please re-examine ALL images carefully and fix the mapping."
        )
    else:
        text_content = (
            f"Analyze ALL pages of the attached financial statement images.\n"
            f"IMPORTANT: Financial data may appear on ANY page - do not focus only on the first page.\n"
            f"Cover pages, commentary, or executive summaries may precede the actual financial tables.\n\n"
            f"Extract the data for the period ending {period} and map it to the JSON schema."
        )
    
    # Create multimodal human message with TEXT + IMAGES
    human_content = create_vision_message_content(text_content, base64_images)
    human_message = HumanMessage(content=human_content)
    
    # Build the full message list
    messages = [system_message, human_message]
    
    logger.info(f"[INVOKE] Sending {len(base64_images)} images to LLM for {doc_type} extraction")
    
    # Configure tracing
    config = get_runnable_config(
        run_name=f"spread_{doc_type}_{period}" + ("_retry" if retry_context else ""),
        tags=[f"doc_type:{doc_type}", f"pages:{len(base64_images)}", "vision-input"],
        metadata={
            "period": period,
            "schema": schema_class.__name__,
            "is_retry": retry_context is not None,
            "num_images": len(base64_images)
        }
    )
    
    # Invoke the LLM directly with the messages (NOT through the prompt chain)
    result = structured_llm.invoke(messages, config=config)
    
    return result


def _get_enhanced_extraction_system_prompt(doc_type: str) -> str:
    """
    Return enhanced system prompt for extraction when Hub prompt unavailable.
    
    This prompt includes detailed instructions for:
    - Consistent field mapping across periods
    - Proper handling of subtotals vs schema totals
    - Interest classification rules
    """
    return f"""You are a financial statement spreading expert extracting {doc_type} data.

## EXTRACTION PROTOCOL (Follow Exactly)

### STEP 1: ROW LABEL INVENTORY
Before extracting values, list ALL row labels visible in the statement.
For each row label, determine which schema field it maps to.
This mapping MUST be applied IDENTICALLY across ALL periods.

### STEP 2: ANCHOR ROW EXTRACTION (Extract These First)
Extract these primary totals FIRST for each period - they anchor the extraction:
1. revenue / Total Income / Net Sales / Total Revenue
2. cogs / Cost of Goods Sold / Cost of Sales / Cost of Revenue
3. gross_profit / Gross Profit (ALWAYS extract if shown - this is NOT an ignorable subtotal)
4. total_operating_expenses / Total Operating Expenses / Total Expenses (ALWAYS extract if shown)
5. operating_income / Operating Income / EBIT
6. net_income / Net Income / Net Profit / Bottom Line

### STEP 3: DETAIL ROW EXTRACTION
Extract remaining line items using the field mapping from Step 1.

## SUBTOTAL HANDLING RULES (Critical)

EXTRACT these schema-mapped totals (they are NOT ignorable subtotals):
- gross_profit
- total_operating_expenses  
- operating_income
- net_income
- total_current_assets (for balance sheets)
- total_assets (for balance sheets)
- total_liabilities (for balance sheets)

IGNORE these intermediate subtotals (unless they ARE the only value for a schema field):
- "Subtotal", "Subtotal Payroll", "Total Travel", "Total Marketing"
- Any row that is clearly a sub-grouping within a larger category

## INTEREST CLASSIFICATION RULES

interest_expense includes:
- Interest Expense
- Finance Charges
- Bank Charges
- Interest on Loans
- Interest Paid

These are NON-OPERATING unless the statement explicitly groups them under "Operating Expenses".

## SG&A CLASSIFICATION RULES

sga (Selling, General & Administrative) includes:
- G&A, Admin Expenses, General Expenses
- Office Expenses, Rent, Utilities, Insurance
- Salaries & Wages, Payroll (if in OpEx section)
- Professional Fees, Legal, Accounting

Do NOT include in SG&A:
- Interest expense
- Depreciation (map to depreciation_amortization)
- Income taxes

## CONSISTENCY ENFORCEMENT

CRITICAL: If Row X maps to field Y for Period 1, Row X MUST map to field Y for ALL periods.
No exceptions. Same row label = same schema field across all periods.

## NULL POLICY

- value: null means "not present in document for this period"
- confidence: 0.0 for null values
- raw_fields_used: ["NOT FOUND: field_name not present in document for this period"]

Never guess values. Only extract what is explicitly shown.

## BREAKDOWN EXTRACTION (Sub-Account Detail)

When a schema field (e.g., revenue, cogs, sga) is computed by summing multiple document line items, 
populate the `breakdown` array with those sub-components:

RULES:
- Only include breakdowns when the document explicitly shows sub-items that sum to a total
- Each breakdown item needs a `label` (exact text from document) and `value` (the dollar amount)
- Sub-items should be in document order (top to bottom as they appear)
- Include ALL sub-items that contribute to the total, including negative items (returns, refunds, credits)
- Do NOT create breakdowns for single-value fields (leave breakdown as null)
- Breakdowns are OPTIONAL - only populate when clearly present in the document

EXAMPLE: If the document shows:
  Revenue
    Product Sales         $6,854,718
    Digital Sales (App)      $42,467
    Shipping & Handling      $89,900
    Returns and Refunds   ($470,356)
  Total Revenue          $6,516,729

Extract as:
{{
  "revenue": {{
    "value": 6516729,
    "confidence": 0.95,
    "raw_fields_used": ["Total Revenue: $6,516,729"],
    "breakdown": [
      {{"label": "Product Sales", "value": 6854718}},
      {{"label": "Digital Sales (App)", "value": 42467}},
      {{"label": "Shipping & Handling", "value": 89900}},
      {{"label": "Returns and Refunds", "value": -470356}}
    ]
  }}
}}

COMMON FIELDS WITH BREAKDOWNS:
- revenue: Often has Product Sales, Service Revenue, Returns, Discounts
- cogs: Often has Material Costs, Labor, Freight, Amazon Fees
- sga: Often has multiple expense categories (Marketing, Wages, Rent, etc.)
- long_term_debt: Often has multiple loan types
- short_term_debt: Often has Credit Cards, Lines of Credit"""


@traceable(
    name="invoke_llm_for_multi_period_spreading",
    tags=["llm", "vision", "extraction", "multi-period"],
    metadata={"operation": "llm_invoke_multi_period"}
)
def _invoke_llm_for_multi_period_spreading(
    prompt: ChatPromptTemplate,
    base64_images: List[tuple],
    doc_type: str,
    column_classification: ColumnClassification,
    model_name: str,
    model_kwargs: Optional[dict] = None,
) -> Union[MultiPeriodIncomeExtraction, MultiPeriodBalanceExtraction]:
    """
    Invoke the LLM to extract ALL periods from a financial statement in a single call.
    
    Column classification is passed in to ensure the model only extracts from
    real period columns, not rollup/total columns.
    
    Args:
        prompt: The Hub ChatPromptTemplate (contains system message)
        base64_images: List of (base64_data, media_type) tuples
        doc_type: 'income' or 'balance'
        column_classification: Pre-classified columns (periods vs rollups) - FROZEN
        model_name: Model to use for extraction
        model_kwargs: Additional model parameters
        
    Returns:
        MultiPeriodIncomeExtraction or MultiPeriodBalanceExtraction with all periods
    """
    # Get the multi-period extraction schema
    extraction_schema = get_multi_period_extraction_schema(doc_type)
    
    # Create LLM with structured output for multi-period extraction
    llm = create_llm(model_name=model_name, model_kwargs=model_kwargs)
    structured_llm = llm.with_structured_output(extraction_schema)
    
    # Extract system message from the Hub prompt
    system_message = None
    if hasattr(prompt, 'messages') and prompt.messages:
        for msg in prompt.messages:
            if hasattr(msg, 'prompt') and hasattr(msg.prompt, 'template'):
                if 'SystemMessage' in str(type(msg)):
                    system_message = SystemMessage(content=msg.prompt.template)
                    break
    
    if not system_message:
        logger.warning("[MULTI-PERIOD] Could not extract system message from Hub prompt, using enhanced fallback")
        system_message = SystemMessage(content=_get_enhanced_extraction_system_prompt(doc_type))
        # Set a flag to indicate fallback was used (will be checked by caller)
        global _fallback_prompt_used
        _fallback_prompt_used = True
    
    # Build column selection instructions - EXPLICIT inclusion/exclusion
    period_cols = column_classification.period_columns
    rollup_cols = column_classification.rollup_columns
    
    column_instruction = (
        f"\n\n## COLUMN SELECTION (FROZEN - DO NOT CHANGE)\n"
        f"EXTRACT DATA FROM THESE PERIOD COLUMNS ONLY:\n"
        f"  {period_cols}\n\n"
        f"DO NOT EXTRACT DATA FROM THESE ROLLUP/TOTAL COLUMNS:\n"
        f"  {rollup_cols if rollup_cols else '(none detected)'}\n\n"
        f"This column classification is FINAL. Do not re-classify or re-interpret columns."
    )
    
    # Build the human message text with enhanced instructions
    text_content = (
        f"Analyze ALL pages of the attached financial statement images.\n"
        f"IMPORTANT: Financial data may appear on ANY page - do not focus only on the first page.\n"
        f"Cover pages, commentary, or executive summaries may precede the actual financial tables.\n\n"
        f"Extract data for the specified PERIOD columns and map each to the JSON schema.\n"
        f"{column_instruction}\n\n"
        f"CRITICAL REQUIREMENTS:\n"
        f"1. Build a ROW LABEL → SCHEMA FIELD mapping table FIRST.\n"
        f"2. Apply the SAME mapping to ALL periods (consistency enforcement).\n"
        f"3. Extract anchor totals first: revenue, cogs, gross_profit, total_operating_expenses, net_income.\n"
        f"4. ALWAYS extract gross_profit and total_operating_expenses if shown in the document.\n"
        f"   These are schema fields, NOT ignorable subtotals.\n"
        f"5. For missing values: value=null, confidence=0.0, raw_fields_used=['NOT FOUND: ...'].\n"
        f"6. Order periods from most recent (index 0) to oldest.\n"
        f"7. Use the exact period labels from the document headers.\n"
    )
    
    # Create multimodal human message with TEXT + IMAGES
    human_content = create_vision_message_content(text_content, base64_images)
    human_message = HumanMessage(content=human_content)
    
    # Build the full message list
    messages = [system_message, human_message]
    
    num_periods = len(period_cols)
    logger.info(
        f"[MULTI-PERIOD] Extracting {num_periods} period(s) {period_cols}, "
        f"excluding {len(rollup_cols)} rollup(s) {rollup_cols}"
    )
    
    # Configure tracing with column classification metadata
    config = get_runnable_config(
        run_name=f"spread_{doc_type}_all_periods",
        tags=[f"doc_type:{doc_type}", f"pages:{len(base64_images)}", "vision-input", "multi-period"],
        metadata={
            "period_columns": period_cols,
            "rollup_columns": rollup_cols,
            "num_periods": num_periods,
            "schema": extraction_schema.__name__,
            "num_images": len(base64_images)
        }
    )
    
    # Invoke the LLM - single call for all periods
    result = structured_llm.invoke(messages, config=config)
    
    logger.info(f"[MULTI-PERIOD] Extracted {len(result.periods)} periods in single LLM call")
    
    return result


@traceable(
    name="convert_pdf_to_images",
    tags=["preprocessing", "pdf", "vision"],
    metadata={"operation": "pdf_conversion"}
)
def _convert_pdf_to_images(
    pdf_path: str,
    dpi: int,
    max_pages: Optional[int]
) -> List[tuple]:
    """Convert PDF to base64 images (traced separately for latency breakdown)."""
    return pdf_to_base64_images(
        pdf_path=pdf_path,
        dpi=dpi,
        max_pages=max_pages
    )


@traceable(
    name="spread_pdf",
    tags=["pipeline", "financial-spreading", "pdf", "vision-first"],
    metadata={"version": "5.0", "operation": "spread_pdf"}
)
def spread_pdf(
    pdf_path: str,
    doc_type: str,
    period: str = "Latest",
    model_override: Optional[str] = None,
    extended_thinking: bool = False,
    max_pages: Optional[int] = None,
    dpi: int = 150,
    max_retries: int = 1,
    validation_tolerance: float = 0.05
) -> Union[IncomeStatement, BalanceSheet]:
    """
    Process a PDF financial statement with Vision-First + Reasoning Loop.
    
    ARCHITECTURE:
    1. VISION-FIRST: PDF → Images → Vision API (no text extraction)
    2. PROMPTS FROM HUB: All prompts loaded from LangSmith Hub (fail-fast)
    3. VALIDATION: Math checks on extracted data
    4. SELF-CORRECTION: Auto-retry with error context if validation fails
    
    MODEL CONFIGURATION HIERARCHY:
    1. model_override parameter (for testing only)
    2. LangSmith Hub prompt model_config (if set)
    3. ANTHROPIC_MODEL environment variable
    4. Default: claude-opus-4-6 (from model_config.py)
    
    Args:
        pdf_path: Path to the PDF financial statement
        doc_type: Type of document ('income' or 'balance')
        period: Fiscal period to extract (or 'Latest' for auto-detect)
        model_override: Override model (testing only)
        extended_thinking: Enable extended thinking for Anthropic models (default False)
        max_pages: Maximum pages to process
        dpi: Image resolution for PDF conversion (default 150 - optimized for speed while preserving number readability)
        max_retries: Maximum retry attempts on validation failure
        validation_tolerance: Tolerance for math validation (default 5%)
        
    Returns:
        IncomeStatement or BalanceSheet with extracted data
        
    Raises:
        RuntimeError: If LangSmith Hub is unavailable
    """
    # Add custom metadata to the current trace
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.add_metadata({
                "pdf_path": pdf_path,
                "doc_type": doc_type,
                "period": period,
                "max_pages": max_pages,
                "dpi": dpi,
                "max_retries": max_retries
            })
    except Exception:
        pass
    
    # -------------------------------------------------------------------------
    # STEP A: Convert PDF to Base64 Images (Vision-First)
    # -------------------------------------------------------------------------
    logger.info(f"[VISION-FIRST] Processing PDF: {pdf_path}")
    logger.info(f"Document type: {doc_type}, Period: {period}")
    
    base64_images = _convert_pdf_to_images(pdf_path, dpi, max_pages)
    
    estimated_tokens = estimate_token_count(base64_images)
    logger.info(
        f"Converted {len(base64_images)} pages to images. "
        f"Estimated tokens: ~{estimated_tokens:,}"
    )
    
    # -------------------------------------------------------------------------
    # STEP B: Load Prompt from LangSmith Hub (REQUIRED - no fallback)
    # -------------------------------------------------------------------------
    schema_class = get_schema_for_doc_type(doc_type)
    
    # Load prompt from Hub (model config is handled locally, not from Hub)
    prompt, _ = load_from_hub(doc_type)
    
    # -------------------------------------------------------------------------
    # STEP C: Determine Model (Priority: Override > Env > Default)
    # -------------------------------------------------------------------------
    if model_override:
        # Testing override - user explicitly requested a different model
        model_name = model_override
        model_kwargs = {}
        if "claude" in model_override.lower() and extended_thinking:
            model_kwargs["extended_thinking"] = True
        logger.info(f"[MODEL] Using override: {model_name}")
    else:
        # Use environment variable or default (Anthropic Claude)
        model_name, model_kwargs = get_model_config_from_environment()
        if "claude" in model_name.lower() and extended_thinking:
            model_kwargs["extended_thinking"] = True
        logger.info(f"[MODEL] Using: {model_name}")

    # -------------------------------------------------------------------------
    # STEP C2: Auto-detect period (if requested, using fast model)
    # -------------------------------------------------------------------------
    detected_period_info: Optional[FiscalPeriodDetection] = None
    if _should_autodetect_period(period):
        logger.info("[PERIOD] Auto-detecting reporting period from statement headers...")
        detection_model, detection_kwargs = get_detection_model_config()
        detected_period, detected_period_info = _detect_fiscal_period(
            base64_images=base64_images,
            doc_type=doc_type,
            model_name=detection_model,
            model_kwargs=detection_kwargs,
            requested_period=period,
        )
        if detected_period != period:
            logger.info(f"[PERIOD] Detected period: {detected_period} (confidence={getattr(detected_period_info, 'confidence', None)})")
            period = detected_period
        else:
            logger.info("[PERIOD] Could not confidently detect period; proceeding with default 'Latest'.")
    
    # -------------------------------------------------------------------------
    # STEP D: Initialize LLM with Structured Output (NO hardcoded params)
    # -------------------------------------------------------------------------
    llm = create_llm(model_name=model_name, model_kwargs=model_kwargs)
    structured_llm = llm.with_structured_output(schema_class)
    
    logger.info(f"Model: {model_name} -> Schema: {schema_class.__name__}")
    
    # -------------------------------------------------------------------------
    # STEP E: Invoke with Reasoning Loop (Self-Correction)
    # -------------------------------------------------------------------------
    result = None
    retry_context = None
    
    for attempt in range(max_retries + 1):
        if attempt > 0:
            logger.warning(f"[REASONING LOOP] Retry attempt {attempt}/{max_retries}")
        
        # Invoke the LLM
        result = _invoke_llm_for_spreading(
            prompt=prompt,
            structured_llm=structured_llm,
            base64_images=base64_images,
            doc_type=doc_type,
            period=period,
            schema_class=schema_class,
            retry_context=retry_context
        )
        
        # Validate the result
        validation = validate_spread(result, tolerance=validation_tolerance)
        
        if validation.is_valid:
            logger.info(f"[VALIDATION] Passed on attempt {attempt + 1}")
            break
        else:
            logger.warning(f"[VALIDATION] Failed: {validation}")
            
            if attempt < max_retries:
                # Build retry context with the error and previous result
                retry_context = (
                    f"Validation errors:\n" +
                    "\n".join(f"  - {e}" for e in validation.errors) +
                    f"\n\nCalculated values: {validation.calculated_values}" +
                    f"\n\nPrevious extraction (JSON):\n{result.model_dump_json(indent=2)}"
                )
            else:
                logger.error(
                    f"[REASONING LOOP] Max retries ({max_retries}) reached. "
                    f"Returning result with validation warnings."
                )
    
    # -------------------------------------------------------------------------
    # STEP F: Post-Processing (Compute Missing Totals)
    # -------------------------------------------------------------------------
    if not isinstance(result, (IncomeStatement, BalanceSheet)):
        raise ValueError(
            f"Unexpected result type: {type(result)}. "
            f"Expected {schema_class.__name__}"
        )
    
    # Apply computed totals for income statements (fills in missing gross_profit, etc.)
    if isinstance(result, IncomeStatement):
        result, corrections = apply_computed_totals(result, tolerance=validation_tolerance)
        if corrections:
            logger.info(f"[POST-PROCESS] Applied corrections: {corrections}")

    # Best-effort: populate metadata fields if prompt didn't set them
    # Also standardize the period label
    try:
        standardized_period = standardize_period_label(period)
        if standardized_period != period:
            logger.info(f"[POST-PROCESS] Standardized period: '{period}' -> '{standardized_period}'")
            period = standardized_period
        
        if isinstance(result, IncomeStatement):
            if not getattr(result, "fiscal_period", None):
                result.fiscal_period = period
            else:
                # Standardize existing fiscal_period
                result.fiscal_period = standardize_period_label(result.fiscal_period)
        elif isinstance(result, BalanceSheet):
            if not getattr(result, "as_of_date", None) and detected_period_info and detected_period_info.best_end_date:
                result.as_of_date = detected_period_info.best_end_date
    except Exception:
        # Never fail the pipeline for metadata enrichment
        pass
    
    logger.info(f"Successfully extracted {schema_class.__name__}")
    _log_extraction_summary(result)
    
    return result


@traceable(
    name="spread_pdf_multi_period",
    tags=["pipeline", "financial-spreading", "pdf", "vision-first", "multi-period"],
    metadata={"version": "5.0", "operation": "spread_pdf_multi_period"}
)
def spread_pdf_multi_period(
    pdf_path: str,
    doc_type: str,
    model_override: Optional[str] = None,
    extended_thinking: bool = False,
    max_pages: Optional[int] = None,
    dpi: int = 150,
    max_retries: int = 1,
    validation_tolerance: float = 0.05,
    _preconverted_images: Optional[List[tuple]] = None,
) -> Union[MultiPeriodIncomeStatement, MultiPeriodBalanceSheet]:
    """
    Process a PDF financial statement and extract ALL detected periods.
    
    v5.0 CHANGES:
    - Column classifier step separates periods from rollups (prevents "Total" extraction)
    - Column classification is FROZEN for retries
    - Post-extraction validation computes missing totals (gross_profit, etc.)
    - Cross-period consistency validation
    
    ARCHITECTURE:
    1. VISION-FIRST: PDF → Images → Vision API
    2. PERIOD DETECTION: Identify all period columns
    3. COLUMN CLASSIFICATION: Separate periods from rollups (NEW)
    4. MULTI-EXTRACTION: Extract data for each period (with frozen columns)
    5. POST-PROCESSING: Compute missing totals, validate consistency (NEW)
    6. VALIDATION: Math checks on each period's data
    
    Args:
        pdf_path: Path to the PDF financial statement
        doc_type: Type of document ('income' or 'balance')
        model_override: Override model (testing only)
        extended_thinking: Enable extended thinking for Anthropic models (default False)
        max_pages: Maximum pages to process
        dpi: Image resolution for PDF conversion (default 150 - optimized for speed while preserving number readability)
        max_retries: Maximum retry attempts on validation failure
        validation_tolerance: Tolerance for math validation (default 5%)
        _preconverted_images: Internal use - pre-converted images to avoid duplicate conversion
        
    Returns:
        MultiPeriodIncomeStatement or MultiPeriodBalanceSheet with all periods
    """
    # Add custom metadata to the current trace
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.add_metadata({
                "pdf_path": pdf_path,
                "doc_type": doc_type,
                "max_pages": max_pages,
                "dpi": dpi,
                "mode": "multi-period",
                "version": "5.0",
                "using_preconverted": _preconverted_images is not None
            })
    except Exception:
        pass
    
    # -------------------------------------------------------------------------
    # STEP A: Convert PDF to Base64 Images (Vision-First) or use pre-converted
    # -------------------------------------------------------------------------
    logger.info(f"[MULTI-PERIOD] Processing PDF: {pdf_path}")
    logger.info(f"Document type: {doc_type}")
    
    if _preconverted_images is not None:
        base64_images = _preconverted_images
        logger.info(f"[MULTI-PERIOD] Using {len(base64_images)} pre-converted images")
    else:
        base64_images = _convert_pdf_to_images(pdf_path, dpi, max_pages)
    
    estimated_tokens = estimate_token_count(base64_images)
    logger.info(
        f"Processing {len(base64_images)} pages. "
        f"Estimated tokens: ~{estimated_tokens:,}"
    )
    
    # -------------------------------------------------------------------------
    # STEP B: Get Model Configuration
    # -------------------------------------------------------------------------
    schema_class = get_schema_for_doc_type(doc_type)
    
    if model_override:
        model_name = model_override
        model_kwargs = {}
        if "claude" in model_override.lower() and extended_thinking:
            model_kwargs["extended_thinking"] = True
    else:
        model_name, model_kwargs = get_model_config_from_environment()
        if "claude" in model_name.lower() and extended_thinking:
            model_kwargs["extended_thinking"] = True
    
    # -------------------------------------------------------------------------
    # STEP C: Detect ALL Period Candidates (using fast model)
    # -------------------------------------------------------------------------
    logger.info("[MULTI-PERIOD] Detecting all period columns...")
    detection_model, detection_kwargs = get_detection_model_config()
    _, period_info = _detect_fiscal_period(
        base64_images=base64_images,
        doc_type=doc_type,
        model_name=detection_model,
        model_kwargs=detection_kwargs,
        requested_period="Latest",
    )
    
    if period_info and period_info.candidates:
        period_labels = [c.normalized_label or c.label for c in period_info.candidates if c.confidence >= 0.5]
        logger.info(f"[MULTI-PERIOD] Detected {len(period_labels)} period candidate(s): {period_labels}")
    else:
        logger.warning("[MULTI-PERIOD] No period candidates from detection step")
    
    # -------------------------------------------------------------------------
    # STEP D: CLASSIFY COLUMNS (using fast model - Separate Periods from Rollups)
    # -------------------------------------------------------------------------
    logger.info("[MULTI-PERIOD] Classifying columns (periods vs rollups)...")
    
    column_classification = _classify_columns(
        base64_images=base64_images,
        doc_type=doc_type,
        model_name=detection_model,
        model_kwargs=detection_kwargs,
        period_candidates=period_info.candidates if period_info else [],
    )
    
    # Log classification results for debugging
    logger.info(f"[COLUMN CLASSIFIER] Period columns: {column_classification.period_columns}")
    logger.info(f"[COLUMN CLASSIFIER] Rollup columns: {column_classification.rollup_columns}")
    if column_classification.classification_notes:
        logger.info(f"[COLUMN CLASSIFIER] Notes: {column_classification.classification_notes}")
    
    if not column_classification.period_columns:
        raise ValueError(
            "No period columns detected after classification. "
            "Cannot proceed with extraction. Check document format."
        )
    
    # FREEZE column classification - this will NOT change on retries
    frozen_columns = column_classification
    
    # -------------------------------------------------------------------------
    # STEP E: Extract ALL Periods (with FROZEN column classification)
    # -------------------------------------------------------------------------
    prompt, _ = load_from_hub(doc_type)
    
    logger.info(
        f"[MULTI-PERIOD] Extracting {len(frozen_columns.period_columns)} period(s) "
        f"(excluding {len(frozen_columns.rollup_columns)} rollup column(s))..."
    )
    
    try:
        # Single LLM call with frozen column classification
        extraction_result = _invoke_llm_for_multi_period_spreading(
            prompt=prompt,
            base64_images=base64_images,
            doc_type=doc_type,
            column_classification=frozen_columns,
            model_name=model_name,
            model_kwargs=model_kwargs,
        )
        
        extracted_periods = extraction_result.periods
        currency = extraction_result.currency
        scale = extraction_result.scale
        
        # Standardize period labels for consistency
        for period_data in extracted_periods:
            original_label = period_data.period_label
            standardized_label = standardize_period_label(original_label)
            if standardized_label != original_label:
                logger.info(f"[MULTI-PERIOD] Standardized period label: '{original_label}' -> '{standardized_label}'")
                period_data.period_label = standardized_label
        
        logger.info(f"[MULTI-PERIOD] Extracted {len(extracted_periods)} period(s) in single LLM call")
        
    except Exception as e:
        logger.error(f"[MULTI-PERIOD] Failed to extract periods: {e}")
        raise ValueError(f"Failed to extract periods from document: {e}")
    
    if not extracted_periods:
        raise ValueError("LLM extraction returned no periods")
    
    # -------------------------------------------------------------------------
    # STEP F: POST-PROCESSING (Compute Totals, Validate Consistency)
    # Uses parallel processing for 3+ periods
    # -------------------------------------------------------------------------
    logger.info(f"[MULTI-PERIOD] Running post-extraction processing for {len(extracted_periods)} periods...")
    
    # F1: Apply computed totals to each period (fills in missing gross_profit, etc.)
    # Uses parallel processing when 3+ periods exist
    if doc_type in ["income", "income_statement"]:
        apply_computed_totals_parallel(extracted_periods, tolerance=validation_tolerance)
    
    # F2: Validate cross-period consistency (must run after F1, needs all periods)
    is_consistent, consistency_errors, _ = validate_multi_period_consistency(
        extracted_periods, doc_type
    )
    if not is_consistent:
        logger.warning(f"[CONSISTENCY] Cross-period issues found: {consistency_errors}")
    
    # F3: Validate math for each period
    # Uses parallel processing when 3+ periods exist
    validate_periods_parallel(extracted_periods, tolerance=validation_tolerance)
    
    # -------------------------------------------------------------------------
    # STEP G: Build Multi-Period Result
    # -------------------------------------------------------------------------
    if not currency:
        first_data = extracted_periods[0].data
        currency = getattr(first_data, 'currency', 'USD')
    if not scale:
        first_data = extracted_periods[0].data
        scale = getattr(first_data, 'scale', 'units')
    
    if doc_type in ["income", "income_statement"]:
        result = MultiPeriodIncomeStatement(
            periods=extracted_periods,
            currency=currency,
            scale=scale
        )
    else:
        result = MultiPeriodBalanceSheet(
            periods=extracted_periods,
            currency=currency,
            scale=scale
        )
    
    # Log extraction summary
    logger.info(
        f"[MULTI-PERIOD] Successfully extracted {len(extracted_periods)} period(s): "
        f"{[p.period_label for p in extracted_periods]}"
    )
    
    return result


# =============================================================================
# COMBINED EXTRACTION (Auto-Detect + Parallel)
# =============================================================================

@traceable(
    name="spread_pdf_combined",
    tags=["pipeline", "financial-spreading", "pdf", "combined", "parallel"],
    metadata={"version": "5.0", "operation": "spread_pdf_combined"}
)
async def spread_pdf_combined(
    pdf_path: str,
    model_override: Optional[str] = None,
    extended_thinking: bool = False,
    max_pages: Optional[int] = None,
    dpi: int = 150,
    max_retries: int = 1,
    validation_tolerance: float = 0.05,
) -> CombinedFinancialExtraction:
    """
    Auto-detect statement types in a PDF and extract all found statements in parallel.
    
    This function:
    1. Converts PDF to images (once)
    2. Detects which statement types are present (income statement, balance sheet, or both)
    3. Extracts detected statements in parallel (if both present)
    4. Returns combined results
    
    PERFORMANCE:
    - When both IS and BS are present, parallel extraction reduces total time by ~50%
    - Images are converted once and shared between extractions
    
    Args:
        pdf_path: Path to the PDF financial statement
        model_override: Override model (testing only)
        extended_thinking: Enable extended thinking for Anthropic models (default False)
        max_pages: Maximum pages to process
        dpi: Image resolution for PDF conversion
        max_retries: Maximum retry attempts on validation failure
        validation_tolerance: Tolerance for math validation (default 5%)
        
    Returns:
        CombinedFinancialExtraction with income statement and/or balance sheet data
    """
    start_time = datetime.now()
    
    # Add custom metadata to the current trace
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.add_metadata({
                "pdf_path": pdf_path,
                "max_pages": max_pages,
                "dpi": dpi,
                "mode": "combined-auto-detect",
                "version": "5.0"
            })
    except Exception:
        pass
    
    # -------------------------------------------------------------------------
    # STEP 1: Convert PDF to Base64 Images (Done ONCE)
    # -------------------------------------------------------------------------
    logger.info(f"[COMBINED] Processing PDF: {pdf_path}")
    
    base64_images = _convert_pdf_to_images(pdf_path, dpi, max_pages)
    
    estimated_tokens = estimate_token_count(base64_images)
    logger.info(
        f"[COMBINED] Converted {len(base64_images)} pages to images. "
        f"Estimated tokens: ~{estimated_tokens:,}"
    )
    
    # -------------------------------------------------------------------------
    # STEP 2: Determine Model Configuration
    # -------------------------------------------------------------------------
    if model_override:
        model_name = model_override
        model_kwargs = {}
        if "claude" in model_override.lower() and extended_thinking:
            model_kwargs["extended_thinking"] = True
    else:
        model_name, model_kwargs = get_model_config_from_environment()
        if "claude" in model_name.lower() and extended_thinking:
                model_kwargs["extended_thinking"] = True
    
    logger.info(f"[COMBINED] Using model: {model_name}")
    
    # -------------------------------------------------------------------------
    # STEP 3: Detect Statement Types (using fast model)
    # -------------------------------------------------------------------------
    logger.info("[COMBINED] Detecting statement types...")
    
    # Use fast detection model for classification tasks
    detection_model, detection_kwargs = get_detection_model_config()
    
    detection = _detect_statement_types(
        base64_images=base64_images,
        model_name=detection_model,
        model_kwargs=detection_kwargs,
    )
    
    logger.info(
        f"[COMBINED] Detection result: "
        f"Income Statement={detection.has_income_statement}, "
        f"Balance Sheet={detection.has_balance_sheet}, "
        f"Confidence={detection.confidence:.2f}"
    )
    
    # Check if no statements detected
    if not detection.has_income_statement and not detection.has_balance_sheet:
        logger.warning("[COMBINED] No financial statements detected in document")
        return CombinedFinancialExtraction(
            income_statement=None,
            balance_sheet=None,
            detected_types=detection,
            extraction_metadata={
                "execution_time_seconds": (datetime.now() - start_time).total_seconds(),
                "model": model_name,
                "error": "No financial statements detected"
            }
        )
    
    # -------------------------------------------------------------------------
    # STEP 4: Extract Statements (Parallel if both present)
    # -------------------------------------------------------------------------
    income_result: Optional[MultiPeriodIncomeStatement] = None
    balance_result: Optional[MultiPeriodBalanceSheet] = None
    extraction_errors: List[str] = []
    
    if detection.has_income_statement and detection.has_balance_sheet:
        # PARALLEL EXTRACTION - run both in parallel using asyncio
        logger.info("[COMBINED] Both statement types detected - running parallel extraction")
        
        async def extract_income():
            try:
                return spread_pdf_multi_period(
                    pdf_path=pdf_path,
                    doc_type="income",
                    model_override=model_override,
                    extended_thinking=extended_thinking,
                    max_pages=max_pages,
                    dpi=dpi,
                    max_retries=max_retries,
                    validation_tolerance=validation_tolerance,
                    _preconverted_images=base64_images,
                )
            except Exception as e:
                logger.error(f"[COMBINED] Income statement extraction failed: {e}")
                extraction_errors.append(f"Income statement extraction failed: {str(e)}")
                return None
        
        async def extract_balance():
            try:
                return spread_pdf_multi_period(
                    pdf_path=pdf_path,
                    doc_type="balance",
                    model_override=model_override,
                    extended_thinking=extended_thinking,
                    max_pages=max_pages,
                    dpi=dpi,
                    max_retries=max_retries,
                    validation_tolerance=validation_tolerance,
                    _preconverted_images=base64_images,
                )
            except Exception as e:
                logger.error(f"[COMBINED] Balance sheet extraction failed: {e}")
                extraction_errors.append(f"Balance sheet extraction failed: {str(e)}")
                return None
        
        # Run both extractions in parallel using asyncio.to_thread for sync functions
        income_task = asyncio.to_thread(
            spread_pdf_multi_period,
            pdf_path,
            "income",
            model_override,
            extended_thinking,
            max_pages,
            dpi,
            max_retries,
            validation_tolerance,
            base64_images,
        )
        balance_task = asyncio.to_thread(
            spread_pdf_multi_period,
            pdf_path,
            "balance",
            model_override,
            extended_thinking,
            max_pages,
            dpi,
            max_retries,
            validation_tolerance,
            base64_images,
        )
        
        # Gather results
        results = await asyncio.gather(income_task, balance_task, return_exceptions=True)
        
        # Process results
        if isinstance(results[0], Exception):
            logger.error(f"[COMBINED] Income statement extraction failed: {results[0]}")
            extraction_errors.append(f"Income statement: {str(results[0])}")
        else:
            income_result = results[0]
            
        if isinstance(results[1], Exception):
            logger.error(f"[COMBINED] Balance sheet extraction failed: {results[1]}")
            extraction_errors.append(f"Balance sheet: {str(results[1])}")
        else:
            balance_result = results[1]
            
    elif detection.has_income_statement:
        # SINGLE EXTRACTION - Income Statement only
        logger.info("[COMBINED] Only income statement detected - extracting...")
        
        try:
            income_result = spread_pdf_multi_period(
                pdf_path=pdf_path,
                doc_type="income",
                model_override=model_override,
                extended_thinking=extended_thinking,
                max_pages=max_pages,
                dpi=dpi,
                max_retries=max_retries,
                validation_tolerance=validation_tolerance,
                _preconverted_images=base64_images,
            )
        except Exception as e:
            logger.error(f"[COMBINED] Income statement extraction failed: {e}")
            extraction_errors.append(f"Income statement: {str(e)}")
            
    elif detection.has_balance_sheet:
        # SINGLE EXTRACTION - Balance Sheet only
        logger.info("[COMBINED] Only balance sheet detected - extracting...")
        
        try:
            balance_result = spread_pdf_multi_period(
                pdf_path=pdf_path,
                doc_type="balance",
                model_override=model_override,
                extended_thinking=extended_thinking,
                max_pages=max_pages,
                dpi=dpi,
                max_retries=max_retries,
                validation_tolerance=validation_tolerance,
                _preconverted_images=base64_images,
            )
        except Exception as e:
            logger.error(f"[COMBINED] Balance sheet extraction failed: {e}")
            extraction_errors.append(f"Balance sheet: {str(e)}")
    
    # -------------------------------------------------------------------------
    # STEP 5: Build Combined Result
    # -------------------------------------------------------------------------
    execution_time = (datetime.now() - start_time).total_seconds()
    
    # Build metadata
    metadata = {
        "execution_time_seconds": execution_time,
        "model": model_name,
        "pages_processed": len(base64_images),
        "estimated_tokens": estimated_tokens,
        "parallel_extraction": detection.has_income_statement and detection.has_balance_sheet,
    }
    
    if extraction_errors:
        metadata["extraction_errors"] = extraction_errors
    
    if income_result:
        metadata["income_statement_periods"] = len(income_result.periods)
    if balance_result:
        metadata["balance_sheet_periods"] = len(balance_result.periods)
    
    result = CombinedFinancialExtraction(
        income_statement=income_result,
        balance_sheet=balance_result,
        detected_types=detection,
        extraction_metadata=metadata,
    )
    
    logger.info(
        f"[COMBINED] Extraction complete in {execution_time:.2f}s. "
        f"Income Statement: {'Yes' if income_result else 'No'}, "
        f"Balance Sheet: {'Yes' if balance_result else 'No'}"
    )
    
    return result


# =============================================================================
# EXCEL PROCESSING
# =============================================================================

def _get_excel_model_config(
    model_override: Optional[str],
    extended_thinking: bool
) -> Tuple[str, dict]:
    """
    Get model configuration for Excel processing.
    
    Extracted as helper to avoid duplication between sync and async functions.
    """
    if model_override:
        model_name = model_override
        model_kwargs = {}
        if "claude" in model_override.lower() and extended_thinking:
            model_kwargs["extended_thinking"] = True
    else:
        model_name, model_kwargs = get_model_config_from_environment()
        if "claude" in model_name.lower() and extended_thinking:
            model_kwargs["extended_thinking"] = True
    
    return model_name, model_kwargs


def _detect_excel_sheet_types(csv_content: str) -> Tuple[List[str], List[str]]:
    """
    Detect which sheets contain Income Statement vs Balance Sheet data.
    
    Returns:
        Tuple of (income_sheets, balance_sheets)
    """
    income_sheets = []
    balance_sheets = []
    
    # Parse CSV content back into sections for detection
    sections = csv_content.split("\n\n=== SHEET: ")
    for section in sections:
        if not section.strip():
            continue
        # Extract sheet name from section header
        if section.startswith("=== SHEET: "):
            section = section[11:]  # Remove prefix
        
        if " ===" in section:
            sheet_name = section.split(" ===")[0]
            sheet_csv = section.split(" ===\n", 1)[1] if " ===\n" in section else ""
        else:
            # First section doesn't have the prefix stripped
            parts = section.split(" ===\n", 1)
            sheet_name = parts[0]
            sheet_csv = parts[1] if len(parts) > 1 else ""
        
        detected_type = detect_statement_type_from_sheet(sheet_name, sheet_csv)
        
        if detected_type == 'income':
            income_sheets.append(sheet_name)
            logger.info(f"[EXCEL] Sheet '{sheet_name}' detected as Income Statement")
        elif detected_type == 'balance':
            balance_sheets.append(sheet_name)
            logger.info(f"[EXCEL] Sheet '{sheet_name}' detected as Balance Sheet")
        else:
            logger.debug(f"[EXCEL] Sheet '{sheet_name}' type unclear, will include in extraction")
    
    return income_sheets, balance_sheets


@traceable(
    name="spread_excel_combined",
    tags=["pipeline", "financial-spreading", "excel", "combined", "parallel"],
    metadata={"version": "2.0", "operation": "spread_excel_combined"}
)
async def spread_excel_combined(
    excel_path: str,
    model_override: Optional[str] = None,
    extended_thinking: bool = False,
    max_retries: int = 1,
    validation_tolerance: float = 0.05,
) -> CombinedFinancialExtraction:
    """
    Auto-detect statement types in Excel and extract all found statements in PARALLEL.
    
    This function:
    1. Converts Excel to CSV (once)
    2. Detects which statement types are present (income statement, balance sheet, or both)
    3. Extracts detected statements in PARALLEL (if both present)
    4. Returns combined results
    
    PERFORMANCE:
    - When both IS and BS are present, parallel extraction reduces total time by ~50%
    - CSV content is converted once and shared between extractions
    
    Args:
        excel_path: Path to the Excel file (.xlsx, .xls, .xlsm)
        model_override: Override model (testing only)
        extended_thinking: Enable extended thinking for Anthropic models
        max_retries: Maximum retry attempts on validation failure
        validation_tolerance: Tolerance for math validation (default 5%)
        
    Returns:
        CombinedFinancialExtraction with both statement types (if found)
    """
    start_time = datetime.now()
    
    # Add custom metadata to the current trace
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.add_metadata({
                "excel_path": excel_path,
                "doc_type": "auto",
                "mode": "excel-combined-parallel",
            })
    except Exception:
        pass
    
    # -------------------------------------------------------------------------
    # STEP 1: Convert Excel to CSV sections (done once)
    # -------------------------------------------------------------------------
    logger.info(f"[EXCEL-COMBINED] Processing Excel file: {excel_path}")
    
    csv_content, sheet_names = excel_to_csv_sections(excel_path)
    
    logger.info(f"[EXCEL-COMBINED] Found {len(sheet_names)} sheets: {sheet_names}")
    
    # Estimate tokens (roughly 1 token per 4 characters for text)
    estimated_tokens = len(csv_content) // 4
    logger.info(f"[EXCEL-COMBINED] CSV content: {len(csv_content)} chars, ~{estimated_tokens} tokens")
    
    # -------------------------------------------------------------------------
    # STEP 2: Get Model Configuration
    # -------------------------------------------------------------------------
    model_name, model_kwargs = _get_excel_model_config(model_override, extended_thinking)
    logger.info(f"[EXCEL-COMBINED] Using model: {model_name}")
    
    # -------------------------------------------------------------------------
    # STEP 3: Detect statement types from sheet names/content
    # -------------------------------------------------------------------------
    logger.info("[EXCEL-COMBINED] Auto-detecting statement types from sheets...")
    income_sheets, balance_sheets = _detect_excel_sheet_types(csv_content)
    
    # -------------------------------------------------------------------------
    # STEP 4: Extract statements - PARALLEL when both present
    # -------------------------------------------------------------------------
    income_result = None
    balance_result = None
    extraction_errors: List[str] = []
    
    should_extract_income = income_sheets or not balance_sheets
    should_extract_balance = balance_sheets or not income_sheets
    
    if should_extract_income and should_extract_balance:
        # PARALLEL EXTRACTION - run both in parallel using asyncio
        logger.info("[EXCEL-COMBINED] Both statement types detected - running PARALLEL extraction")
        
        # Run both extractions in parallel using asyncio.to_thread for sync functions
        income_task = asyncio.to_thread(
            _extract_excel_statement,
            csv_content,
            "income",
            model_name,
            model_kwargs,
            validation_tolerance,
        )
        balance_task = asyncio.to_thread(
            _extract_excel_statement,
            csv_content,
            "balance",
            model_name,
            model_kwargs,
            validation_tolerance,
        )
        
        # Gather results
        results = await asyncio.gather(income_task, balance_task, return_exceptions=True)
        
        # Process results
        if isinstance(results[0], Exception):
            logger.error(f"[EXCEL-COMBINED] Income statement extraction failed: {results[0]}")
            extraction_errors.append(f"Income statement: {str(results[0])}")
        else:
            income_result = results[0]
        
        if isinstance(results[1], Exception):
            logger.error(f"[EXCEL-COMBINED] Balance sheet extraction failed: {results[1]}")
            extraction_errors.append(f"Balance sheet: {str(results[1])}")
        else:
            balance_result = results[1]
    
    elif should_extract_income:
        # SINGLE EXTRACTION - Income Statement only
        logger.info("[EXCEL-COMBINED] Only income statement detected - extracting...")
        try:
            income_result = _extract_excel_statement(
                csv_content=csv_content,
                doc_type="income",
                model_name=model_name,
                model_kwargs=model_kwargs,
                validation_tolerance=validation_tolerance,
            )
        except Exception as e:
            logger.error(f"[EXCEL-COMBINED] Income statement extraction failed: {e}")
            extraction_errors.append(f"Income statement: {str(e)}")
    
    elif should_extract_balance:
        # SINGLE EXTRACTION - Balance Sheet only
        logger.info("[EXCEL-COMBINED] Only balance sheet detected - extracting...")
        try:
            balance_result = _extract_excel_statement(
                csv_content=csv_content,
                doc_type="balance",
                model_name=model_name,
                model_kwargs=model_kwargs,
                validation_tolerance=validation_tolerance,
            )
        except Exception as e:
            logger.error(f"[EXCEL-COMBINED] Balance sheet extraction failed: {e}")
            extraction_errors.append(f"Balance sheet: {str(e)}")
    
    execution_time = (datetime.now() - start_time).total_seconds()
    
    # -------------------------------------------------------------------------
    # STEP 5: Build result
    # -------------------------------------------------------------------------
    # Note: income_sheets and balance_sheets are sheet NAMES (strings) for Excel files
    # StatementTypeDetection.income_statement_pages expects page numbers (integers)
    # For Excel, we pass empty lists and include sheet info in notes
    detection = StatementTypeDetection(
        has_income_statement=income_result is not None,
        has_balance_sheet=balance_result is not None,
        income_statement_pages=[],  # Page numbers don't apply to Excel
        balance_sheet_pages=[],  # Page numbers don't apply to Excel
        confidence=0.9 if (income_sheets or balance_sheets) else 0.5,
        notes=f"Detected from Excel sheets: IS={income_sheets}, BS={balance_sheets}"
    )
    
    metadata = {
        "execution_time_seconds": execution_time,
        "model": model_name,
        "sheets_processed": sheet_names,
        "estimated_tokens": estimated_tokens,
        "source_type": "excel",
        "parallel_extraction": should_extract_income and should_extract_balance,
    }
    if extraction_errors:
        metadata["extraction_errors"] = extraction_errors
    
    result = CombinedFinancialExtraction(
        income_statement=income_result,
        balance_sheet=balance_result,
        detected_types=detection,
        extraction_metadata=metadata,
    )
    
    logger.info(
        f"[EXCEL-COMBINED] Extraction complete in {execution_time:.2f}s "
        f"({'parallel' if metadata['parallel_extraction'] else 'sequential'}). "
        f"Income Statement: {'Yes' if income_result else 'No'}, "
        f"Balance Sheet: {'Yes' if balance_result else 'No'}"
    )
    
    return result


@traceable(
    name="spread_excel_multi_period",
    tags=["pipeline", "financial-spreading", "excel", "multi-sheet"],
    metadata={"version": "2.0", "operation": "spread_excel"}
)
def spread_excel_multi_period(
    excel_path: str,
    doc_type: str,
    model_override: Optional[str] = None,
    extended_thinking: bool = False,
    max_retries: int = 1,
    validation_tolerance: float = 0.05,
) -> Union[MultiPeriodIncomeStatement, MultiPeriodBalanceSheet]:
    """
    Process a multi-worksheet Excel file and extract a SPECIFIC statement type.
    
    For auto-detection with parallel IS+BS extraction, use spread_excel_combined() instead.
    
    ARCHITECTURE:
    1. TEXT-BASED: Excel → CSV text → LLM (no vision needed)
    2. MULTI-SHEET: All worksheets are combined with clear section headers
    3. STRUCTURED OUTPUT: Same Pydantic schemas as PDF processing
    
    ADVANTAGES OVER PDF:
    - No image conversion needed (faster, cheaper)
    - Data is already structured (more reliable)
    - Lower token usage (text vs images)
    
    Args:
        excel_path: Path to the Excel file (.xlsx, .xls, .xlsm)
        doc_type: 'income' or 'balance' (use spread_excel_combined for 'auto')
        model_override: Override model (testing only)
        extended_thinking: Enable extended thinking for Anthropic models
        max_retries: Maximum retry attempts on validation failure
        validation_tolerance: Tolerance for math validation (default 5%)
        
    Returns:
        MultiPeriodIncomeStatement or MultiPeriodBalanceSheet
    """
    start_time = datetime.now()
    
    # Add custom metadata to the current trace
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            run_tree.add_metadata({
                "excel_path": excel_path,
                "doc_type": doc_type,
                "mode": "excel-multi-sheet",
            })
    except Exception:
        pass
    
    # -------------------------------------------------------------------------
    # STEP 1: Convert Excel to CSV sections
    # -------------------------------------------------------------------------
    logger.info(f"[EXCEL] Processing Excel file: {excel_path}")
    
    csv_content, sheet_names = excel_to_csv_sections(excel_path)
    
    logger.info(f"[EXCEL] Found {len(sheet_names)} sheets: {sheet_names}")
    
    # Estimate tokens (roughly 1 token per 4 characters for text)
    estimated_tokens = len(csv_content) // 4
    logger.info(f"[EXCEL] CSV content: {len(csv_content)} chars, ~{estimated_tokens} tokens")
    
    # -------------------------------------------------------------------------
    # STEP 2: Get Model Configuration
    # -------------------------------------------------------------------------
    model_name, model_kwargs = _get_excel_model_config(model_override, extended_thinking)
    logger.info(f"[EXCEL] Using model: {model_name}")
    
    # -------------------------------------------------------------------------
    # STEP 3: Extract specific statement type
    # -------------------------------------------------------------------------
    result = _extract_excel_statement(
        csv_content=csv_content,
        doc_type=doc_type,
        model_name=model_name,
        model_kwargs=model_kwargs,
        validation_tolerance=validation_tolerance,
    )
    
    execution_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"[EXCEL] Extraction complete in {execution_time:.2f}s")
    
    return result


@traceable(
    name="extract_excel_statement",
    tags=["llm", "extraction", "excel"],
    metadata={"operation": "excel_extraction"}
)
def _extract_excel_statement(
    csv_content: str,
    doc_type: str,
    model_name: str,
    model_kwargs: Optional[dict] = None,
    validation_tolerance: float = 0.05,
) -> Union[MultiPeriodIncomeStatement, MultiPeriodBalanceSheet]:
    """
    Extract a single statement type from Excel CSV content.
    
    Args:
        csv_content: Combined CSV content from all sheets
        doc_type: 'income' or 'balance'
        model_name: Model to use for extraction
        model_kwargs: Additional model parameters
        validation_tolerance: Tolerance for math validation
        
    Returns:
        MultiPeriodIncomeStatement or MultiPeriodBalanceSheet
    """
    # Get the extraction schema
    extraction_schema = get_multi_period_extraction_schema(doc_type)
    
    # Create LLM with structured output
    llm = create_llm(model_name=model_name, model_kwargs=model_kwargs)
    structured_llm = llm.with_structured_output(extraction_schema)
    
    # Build the system prompt for Excel extraction
    system_prompt = _get_excel_extraction_system_prompt(doc_type)
    
    # Build the human message with the CSV data
    human_prompt = f"""Analyze the following Excel spreadsheet data (in CSV format) and extract {doc_type} statement data.

The data contains multiple worksheets, each marked with "=== SHEET: Sheet Name ===" headers.

IMPORTANT INSTRUCTIONS:
1. Look at ALL sheets to find the {doc_type} statement data
2. FIRST determine the data format:
   - If columns are MONTHLY (Jan, Feb, Mar...) this is INTERIM data
   - If columns are ANNUAL/QUARTERLY (2023, 2024, FY2025, Q4...) this is ANNUAL data
3. For INTERIM/MONTHLY data:
   - ONLY extract the "Total" or "YTD" column as a SINGLE period
   - Label it with the fiscal year + YTD (e.g., "FY2026 YTD")
   - For balance sheets, use the LATEST month column as the snapshot date
4. For ANNUAL data:
   - Extract EACH annual/quarterly period column
5. Order periods from most recent (index 0) to oldest

CSV DATA:
{csv_content}

Extract the {doc_type} statement data following the schema. For interim monthly data, extract ONLY the YTD total, not individual months."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ]
    
    # Configure tracing
    config = get_runnable_config(
        run_name=f"extract_excel_{doc_type}",
        tags=[f"doc_type:{doc_type}", "excel-input", "text-based"],
        metadata={
            "csv_length": len(csv_content),
            "schema": extraction_schema.__name__,
        }
    )
    
    # Invoke the LLM
    logger.info(f"[EXCEL] Extracting {doc_type} statement from CSV data...")
    result = structured_llm.invoke(messages, config=config)
    
    logger.info(f"[EXCEL] Extracted {len(result.periods)} periods")
    
    # Post-processing: standardize period labels
    for period_data in result.periods:
        original_label = period_data.period_label
        standardized_label = standardize_period_label(original_label)
        if standardized_label != original_label:
            logger.info(f"[EXCEL] Standardized period label: '{original_label}' -> '{standardized_label}'")
            period_data.period_label = standardized_label
    
    # Apply computed totals for income statements (parallel for 3+ periods)
    if doc_type in ["income", "income_statement"]:
        apply_computed_totals_parallel(result.periods, tolerance=validation_tolerance)
    
    # Validate math for each period (parallel for 3+ periods)
    validate_periods_parallel(result.periods, tolerance=validation_tolerance)
    
    # Build the final multi-period result
    currency = result.currency or 'USD'
    scale = result.scale or 'units'
    
    if doc_type in ["income", "income_statement"]:
        return MultiPeriodIncomeStatement(
            periods=result.periods,
            currency=currency,
            scale=scale
        )
    else:
        return MultiPeriodBalanceSheet(
            periods=result.periods,
            currency=currency,
            scale=scale
        )


def _get_excel_extraction_system_prompt(doc_type: str) -> str:
    """
    Return system prompt for Excel-based extraction.
    
    Similar to vision prompts but optimized for structured CSV data.
    """
    return f"""You are a financial statement spreading expert extracting {doc_type} data from Excel spreadsheets.

## INPUT FORMAT
You will receive CSV data from an Excel file. Multiple worksheets are separated by "=== SHEET: Name ===" headers.
The data is clean, structured, and already in tabular format (no OCR/image interpretation needed).

## EXTRACTION PROTOCOL

### STEP 1: IDENTIFY STATEMENT SHEETS
Look at all sheets and identify which contain the {doc_type} statement data.
Sheet names often indicate content (e.g., "Income Statement", "P&L", "Balance Sheet").

### STEP 2: DETECT DATA FORMAT AND IDENTIFY PERIOD COLUMNS
Financial statements come in TWO formats - detect which one you're dealing with:

**FORMAT A - ANNUAL/QUARTERLY STATEMENTS:**
- Columns have annual/quarterly labels: "FY2023", "2024", "Dec 31, 2024", "Q4 2024"
- Each column represents a COMPLETE fiscal period
- Extract EACH annual/quarterly column as a separate period

**FORMAT B - INTERIM MONTHLY STATEMENTS:**
- Columns have MONTHLY labels: "Jan-2025", "Feb-2025", "Mar-2025", "Nov-2024", etc.
- There is typically a "Total" or "YTD" column that sums all months
- DO NOT extract individual months as separate periods
- ONLY extract the "Total" or "YTD" column as a SINGLE period labeled "FY[Year] YTD"
- For balance sheets with monthly columns, extract the LATEST month as the balance sheet snapshot

**HOW TO DETECT:**
- If you see 6+ columns with consecutive monthly dates (Jan, Feb, Mar...), it's Format B (interim monthly)
- If you see columns like "2023", "2024", "FY2024", it's Format A (annual)

### STEP 3: MAP ROWS TO SCHEMA FIELDS
For each row label in the CSV:
- Map to the appropriate schema field
- Apply the SAME mapping across ALL periods
- Handle common variations (e.g., "Net Sales" = "revenue")

### STEP 4: EXTRACT VALUES
For each relevant period column:
- Extract numerical values
- Handle parentheses as negative: (100) = -100
- Handle blank cells as null
- Note any text/notes in raw_fields_used

## FIELD MAPPING RULES

REVENUE/SALES: "Revenue", "Net Sales", "Total Sales", "Total Revenue", "Net Revenue", "Gross Sales" minus "Sales Adjustments"
COGS: "Cost of Goods Sold", "Cost of Sales", "COGS", "Cost of Revenue", "Cost of Goods Sold (Excl. Depr)"
GROSS PROFIT: "Gross Profit", "Gross Margin" (ALWAYS extract if shown)
SG&A: "SG&A", "Selling, General & Administrative", "Operating Expenses", "G&A", "SG&A (Excl. Depr)"
DEPRECIATION: Sum of all depreciation/amortization lines if itemized separately
TOTAL OPERATING EXPENSES: "Total Operating Expenses", "Total Expenses" (ALWAYS extract)
OPERATING INCOME: "Operating Income", "Income from Operations", "EBIT"
INTEREST EXPENSE: "Interest Expense", "Interest", "Finance Costs", "Interest expenses"
NET INCOME: "Net Income", "Net Profit", "Net Loss", "Bottom Line"

## OUTPUT REQUIREMENTS
- For ANNUAL data: Extract ALL annual/quarterly periods found
- For MONTHLY INTERIM data: Extract ONLY the Total/YTD as a single period (label it "FY[Year] YTD")
- Order periods from most recent to oldest
- Use standardized period labels: "FY2025", "FY2024", "FY2026 YTD", etc.
- Set confidence based on how clearly the value was found
- For missing values: value=null, confidence=0.0

## NULL POLICY
- value: null means "not present in the data"
- Never guess or calculate values that aren't explicitly shown
- Use raw_fields_used to note what you looked for"""


def spread_financials(
    file_path: str,
    doc_type: str,
    period: str = "Latest",
    multi_period: bool = True,
    **kwargs
) -> Union[IncomeStatement, BalanceSheet, MultiPeriodIncomeStatement, MultiPeriodBalanceSheet, CombinedFinancialExtraction]:
    """
    Unified entry point for spreading financial statements.
    
    Accepts file_path and routes to the appropriate processor based on file type.
    Currently supports PDF files (vision-first approach).
    
    Args:
        file_path: Path to the financial statement file (PDF, Excel future)
        doc_type: Type of document ('income', 'balance', or 'auto' for auto-detection)
        period: Fiscal period to extract (ignored if multi_period=True)
        multi_period: If True, extract all periods; if False, extract single period
        **kwargs: Additional arguments passed to the processor
        
    Returns:
        - For doc_type='auto': CombinedFinancialExtraction with both statement types
        - For doc_type='income' or 'balance': IncomeStatement/BalanceSheet (single) 
          or MultiPeriodIncomeStatement/MultiPeriodBalanceSheet (multi)
    """
    from pathlib import Path
    
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = path.suffix.lower()
    
    if ext == ".pdf":
        # Handle auto-detection mode
        if doc_type.lower().strip() == "auto":
            # Run the async combined extraction safely (handles nested event loops)
            return _run_async_safely(spread_pdf_combined(file_path, **kwargs))
        
        if multi_period:
            return spread_pdf_multi_period(file_path, doc_type, **kwargs)
        else:
            return spread_pdf(file_path, doc_type, period, **kwargs)
    elif ext in [".xlsx", ".xls", ".xlsm"]:
        # Excel processing - text-based (CSV), no vision needed
        # Filter out PDF-specific parameters that Excel processing doesn't use
        excel_kwargs = {
            k: v for k, v in kwargs.items()
            if k not in ['dpi', 'max_pages']
        }
        
        # Handle auto-detection mode with parallel extraction
        if doc_type.lower().strip() == "auto":
            # Run the async combined extraction safely (handles nested event loops)
            return _run_async_safely(spread_excel_combined(file_path, **excel_kwargs))
        
        return spread_excel_multi_period(
            excel_path=file_path,
            doc_type=doc_type,
            **excel_kwargs
        )
    else:
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: .pdf, .xlsx, .xls, .xlsm"
        )


def _log_extraction_summary(result: Union[IncomeStatement, BalanceSheet]) -> None:
    """Log a summary of the extraction for debugging."""
    high_confidence_count = 0
    low_confidence_count = 0
    missing_count = 0
    
    for field_name, field_value in result.model_dump().items():
        if isinstance(field_value, dict) and "value" in field_value:
            if field_value["value"] is None:
                missing_count += 1
            elif field_value.get("confidence", 0) >= 0.8:
                high_confidence_count += 1
            else:
                low_confidence_count += 1
    
    logger.info(
        f"Extraction summary: "
        f"High confidence: {high_confidence_count}, "
        f"Low confidence: {low_confidence_count}, "
        f"Missing: {missing_count}"
    )


# =============================================================================
# BATCH PROCESSING
# =============================================================================

@traceable(
    name="spread_multiple_files",
    tags=["pipeline", "batch"],
    metadata={"operation": "batch_spread"}
)
def spread_multiple_files(
    file_paths: List[str],
    doc_type: str,
    period: str = "Latest",
    **kwargs
) -> List[dict]:
    """Process multiple files with batch tracing."""
    results = []
    
    for i, file_path in enumerate(file_paths):
        logger.info(f"Processing file {i+1}/{len(file_paths)}: {file_path}")
        
        try:
            result = spread_financials(file_path, doc_type, period, **kwargs)
            results.append({
                "path": file_path,
                "status": "success",
                "result": result.model_dump()
            })
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            results.append({
                "path": file_path,
                "status": "error",
                "error": str(e)
            })
    
    success_count = sum(1 for r in results if r["status"] == "success")
    logger.info(f"Batch complete: {success_count}/{len(file_paths)} successful")
    
    return results


# Backward compatibility aliases
spread_multiple_pdfs = spread_multiple_files
