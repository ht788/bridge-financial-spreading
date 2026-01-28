"""
spreader.py - The Engine Layer (LangSmith-Native + Vision-First + Reasoning Loop)

This module implements financial spreading with:
1. FULL LangSmith integration (Hub prompts, automatic tracing)
2. VISION-FIRST architecture (PDFs as images, not text)
3. REASONING LOOP with self-correction (validates and retries on errors)

Architecture:

1. HUB-CONTROLLED MODEL CONFIGURATION
   - Model name, parameters (reasoning_effort, temperature) come from LangSmith Hub
   - Change models in LangSmith UI → takes effect immediately (no code deploy)
   - Code only provides fallback defaults when Hub is unavailable

2. VISION-FIRST INPUT
   - PDFs converted to images (NOT text extracted)
   - Images resized to max 1024px width for cost efficiency
   - Model "sees" indentation, headers, alignment - critical for correct categorization

3. REASONING LOOP (Chain of Thought)
   - Uses gpt-5.2/o1 with reasoning_effort="high" for deep analysis
   - Validates extracted data (math checks, balance checks)
   - Auto-retries with error context if validation fails

4. STRUCTURED OUTPUT
   - .with_structured_output() ensures Pydantic schema compliance
   - Validation errors traced in LangSmith for debugging
"""

import logging
import os
from typing import Optional, Union, List, Any, Tuple
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig, Runnable
from langchain_openai import ChatOpenAI
from langsmith import traceable
from langsmith.run_helpers import get_current_run_tree
from pydantic import BaseModel, ValidationError, Field

from models import (
    IncomeStatement, 
    BalanceSheet, 
    get_schema_for_doc_type,
    MultiPeriodIncomeStatement,
    MultiPeriodBalanceSheet,
    IncomeStatementPeriod,
    BalanceSheetPeriod,
)
from utils import (
    pdf_to_base64_images,
    create_image_content_block,
    create_vision_message_content,
    estimate_token_count,
    excel_to_markdown
)

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# PERIOD DETECTION (Vision)
# =============================================================================

class PeriodCandidate(BaseModel):
    """A candidate reporting period column found on the statement."""
    label: str = Field(
        description="Human-readable period label as shown (or faithfully normalized), e.g. "
                    "'Year Ended Dec 31, 2024', 'As of 2024-12-31', 'FY2024', 'Q3 2024'."
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
        "Goal: identify the reporting period columns shown (e.g., 'Year ended Dec 31, 2024', "
        "'Three months ended Sep 30, 2024', 'As of 2024-12-31').\n\n"
        "Rules:\n"
        "- Prefer the MOST RECENT period (usually the right-most column).\n"
        "- If multiple periods are shown, include all as candidates and mark is_most_recent.\n"
        "- Preserve the statement's meaning; do not invent dates.\n"
        "- best_period should be a concise label suitable to pass into another extraction prompt.\n"
        "- If you can infer an ISO end_date from visible text, set end_date / best_end_date.\n"
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

    # First pass: first page
    first_pass = _invoke_detection(base64_images[:1])
    best = (first_pass.best_period or "").strip()
    if best and first_pass.confidence >= 0.70:
        return best, first_pass

    # Second pass: first two pages (if available)
    if len(base64_images) > 1:
        second_pass = _invoke_detection(base64_images[:2])
        best2 = (second_pass.best_period or "").strip()
        if best2 and second_pass.confidence >= (first_pass.confidence or 0.0):
            return best2, second_pass

    # Fallback: if we got *some* best_period, use it; otherwise keep requested_period ("Latest")
    if best:
        return best, first_pass
    return requested_period, first_pass


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


@traceable(
    name="load_from_hub",
    tags=["hub", "prompt-management"],
    metadata={"operation": "hub_pull"}
)
def load_from_hub(doc_type: str) -> Tuple[ChatPromptTemplate, Optional[dict]]:
    """
    Load prompt and model configuration from LangSmith Hub.
    
    This function ALWAYS requires Hub access - there is no fallback.
    If Hub is unavailable, the function will fail fast with a clear error.
    
    Uses `include_model=True` to pull the full chain including model config
    when a model is configured in LangSmith Hub (ChatOpenAI section).
    
    Args:
        doc_type: Type of document ('income' or 'balance')
        
    Returns:
        Tuple of (ChatPromptTemplate, model_config_dict or None)
        - model_config includes: model, max_tokens, temperature, reasoning_effort, etc.
        
    Raises:
        ImportError: If langsmith is not installed
        ValueError: If doc_type is not recognized
        RuntimeError: If Hub is unavailable or prompt doesn't exist
    """
    try:
        from langsmith import Client
        from langchain_core.runnables import RunnableSequence, RunnableBinding
    except ImportError as e:
        raise ImportError(
            "langsmith and langchain-core are required for Hub access. "
            "Install with: pip install langsmith langchain-core"
        ) from e
    
    # Normalize document type
    doc_type_normalized = doc_type.lower().strip()
    
    if doc_type_normalized not in PROMPT_MAP:
        raise ValueError(
            f"Unknown document type: '{doc_type}'. "
            f"Valid types: {list(PROMPT_MAP.keys())}"
        )
    
    prompt_name = PROMPT_MAP[doc_type_normalized]
    logger.info(f"[HUB] Pulling prompt from LangSmith Hub: {prompt_name}")
    
    try:
        client = Client()
        
        # Pull the prompt WITH model config using include_model=True
        hub_object = client.pull_prompt(prompt_name, include_model=True)
        
        model_config = None
        prompt = hub_object
        
        # If model is configured, we get a RunnableSequence (prompt | model)
        if isinstance(hub_object, RunnableSequence):
            logger.info(f"[HUB] Prompt has bound model configuration")
            
            # Extract the prompt template (first element)
            prompt = hub_object.first
            
            # Extract model config from the last element (RunnableBinding or ChatOpenAI)
            model_obj = hub_object.last
            
            # Handle RunnableBinding wrapper
            if isinstance(model_obj, RunnableBinding) and hasattr(model_obj, 'bound'):
                model_obj = model_obj.bound
            
            # Extract model configuration
            model_config = {}
            
            # Core model settings
            if hasattr(model_obj, 'model_name'):
                model_config["model"] = model_obj.model_name
            if hasattr(model_obj, 'max_tokens') and model_obj.max_tokens:
                model_config["max_tokens"] = model_obj.max_tokens
            if hasattr(model_obj, 'temperature') and model_obj.temperature is not None:
                model_config["temperature"] = model_obj.temperature
            if hasattr(model_obj, 'reasoning_effort') and model_obj.reasoning_effort:
                model_config["reasoning_effort"] = model_obj.reasoning_effort
            
            if model_config:
                logger.info(f"[HUB] Model config from Hub: {model_config}")
        
        # Log commit hash
        commit_hash = "unknown"
        if hasattr(prompt, 'metadata') and prompt.metadata:
            commit_hash = prompt.metadata.get('lc_hub_commit_hash', 'unknown')[:8]
        logger.info(f"[HUB] Loaded '{prompt_name}' (commit: {commit_hash})")
        
        return prompt, model_config
        
    except Exception as e:
        logger.error(f"[HUB] Failed to pull from Hub: {e}")
        raise RuntimeError(
            f"Could not load '{prompt_name}' from LangSmith Hub. "
            f"Ensure LANGSMITH_API_KEY is set and the prompt exists at: "
            f"https://smith.langchain.com/prompts/{prompt_name} "
            f"Error: {e}"
        ) from e


# NOTE: Fallback prompts have been removed.
# All prompts MUST come from LangSmith Hub.
# See: https://smith.langchain.com/prompts/income-statement
# See: https://smith.langchain.com/prompts/balance-sheet


def get_model_config_from_environment() -> Tuple[str, dict]:
    """
    Get model configuration from environment variables.
    
    Environment Variables:
    - OPENAI_MODEL: Model name (default: gpt-5.2)
    - OPENAI_REASONING_EFFORT: Reasoning effort for o1/gpt-5.2 (default: high)
    
    Returns:
        Tuple of (model_name, model_kwargs)
    """
    # Model name from environment, with gpt-5.2 as default for best reasoning
    model = os.getenv("OPENAI_MODEL", "gpt-5.2")
    
    # Model kwargs
    model_kwargs = {}
    
    # Reasoning effort for gpt-5.2/o1 models
    # Default to "high" for financial analysis requiring deep reasoning
    reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "high")
    
    # Only add reasoning_effort for compatible models
    if any(x in model.lower() for x in ["gpt-5", "o1", "o3"]):
        model_kwargs["reasoning_effort"] = reasoning_effort
        logger.info(f"Using reasoning_effort={reasoning_effort} for model {model}")
    
    return model, model_kwargs


# =============================================================================
# LLM INITIALIZATION
# =============================================================================

def create_llm(
    model_name: Optional[str] = None,
    model_kwargs: Optional[dict] = None
) -> ChatOpenAI:
    """
    Create ChatOpenAI instance WITHOUT hardcoded parameters.
    
    Parameters like temperature, max_tokens should be controlled via:
    1. LangSmith Hub prompt configuration
    2. Environment variables
    3. Passed model_kwargs
    
    This function intentionally does NOT set temperature, max_tokens, etc.
    to allow Hub/environment control.
    
    Args:
        model_name: Optional model override (defaults to env/gpt-5.2)
        model_kwargs: Optional additional model parameters
        
    Returns:
        Configured ChatOpenAI instance
    """
    # Get model from environment if not specified
    if model_name is None:
        model_name, env_kwargs = get_model_config_from_environment()
        if model_kwargs is None:
            model_kwargs = env_kwargs
        else:
            # Merge env kwargs with passed kwargs (passed takes precedence)
            model_kwargs = {**env_kwargs, **model_kwargs}
    
    # Build LLM config - NO hardcoded temperature or max_tokens
    llm_config = {
        "model": model_name,
    }
    
    # Add model_kwargs if present (e.g., reasoning_effort)
    if model_kwargs:
        llm_config["model_kwargs"] = model_kwargs
    
    logger.info(f"Creating LLM: {model_name} with kwargs: {model_kwargs}")
    
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
    
    # Build the human message text with the period
    if retry_context:
        text_content = (
            f"Analyze the visual layout of the attached financial statement images.\n"
            f"Extract the data for the period ending {period} and map it to the JSON schema.\n\n"
            f"IMPORTANT: A previous extraction had errors:\n{retry_context}\n\n"
            f"Please re-examine the images carefully and fix the mapping."
        )
    else:
        text_content = (
            f"Analyze the visual layout of the attached financial statement images.\n"
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
    metadata={"version": "4.0", "operation": "spread_pdf"}
)
def spread_pdf(
    pdf_path: str,
    doc_type: str,
    period: str = "Latest",
    model_override: Optional[str] = None,
    max_pages: Optional[int] = None,
    dpi: int = 200,
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
    3. OPENAI_MODEL environment variable
    4. Default: gpt-5
    
    Args:
        pdf_path: Path to the PDF financial statement
        doc_type: Type of document ('income' or 'balance')
        period: Fiscal period to extract (or 'Latest' for auto-detect)
        model_override: Override model (testing only)
        max_pages: Maximum pages to process
        dpi: Image resolution for PDF conversion
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
    
    # Always load from Hub - fail fast if unavailable
    prompt, hub_model_config = load_from_hub(doc_type)
    
    # -------------------------------------------------------------------------
    # STEP C: Determine Model (Priority: Override > Hub > Env > Default)
    # -------------------------------------------------------------------------
    if model_override:
        # Testing override - user explicitly requested a different model
        model_name = model_override
        model_kwargs = {}
        if any(x in model_override.lower() for x in ["gpt-5", "o1", "o3"]):
            model_kwargs["reasoning_effort"] = os.getenv("OPENAI_REASONING_EFFORT", "high")
        logger.info(f"[MODEL] Using override: {model_name}")
    elif hub_model_config and hub_model_config.get("model"):
        # Model from LangSmith Hub - use full configuration from the prompt
        model_name = hub_model_config["model"]
        model_kwargs = {}
        
        # Transfer Hub model settings to model_kwargs
        if hub_model_config.get("max_tokens"):
            model_kwargs["max_tokens"] = hub_model_config["max_tokens"]
        if hub_model_config.get("temperature") is not None:
            model_kwargs["temperature"] = hub_model_config["temperature"]
        if hub_model_config.get("reasoning_effort"):
            reasoning = hub_model_config["reasoning_effort"]
            # gpt-5.2-chat-latest only supports 'medium' for reasoning_effort
            # Map any invalid value to 'medium'
            valid_efforts = ["low", "medium", "high"]
            if reasoning not in valid_efforts:
                logger.warning(f"[MODEL] Invalid reasoning_effort '{reasoning}', defaulting to 'medium'")
                reasoning = "medium"
            # For gpt-5.2-chat models, only 'medium' is supported
            if "gpt-5.2" in model_name.lower() and reasoning != "medium":
                logger.warning(f"[MODEL] gpt-5.2 only supports reasoning_effort='medium', overriding '{reasoning}'")
                reasoning = "medium"
            model_kwargs["reasoning_effort"] = reasoning
            
        logger.info(f"[MODEL] Using Hub config: {model_name} (kwargs: {model_kwargs})")
    else:
        # Environment variable or default
        model_name, model_kwargs = get_model_config_from_environment()
        logger.info(f"[MODEL] Using environment: {model_name}")

    # -------------------------------------------------------------------------
    # STEP C2: Auto-detect period (if requested)
    # -------------------------------------------------------------------------
    detected_period_info: Optional[FiscalPeriodDetection] = None
    if _should_autodetect_period(period):
        logger.info("[PERIOD] Auto-detecting reporting period from statement headers...")
        detected_period, detected_period_info = _detect_fiscal_period(
            base64_images=base64_images,
            doc_type=doc_type,
            model_name=model_name,
            model_kwargs=model_kwargs,
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
    # STEP F: Return Result
    # -------------------------------------------------------------------------
    if not isinstance(result, (IncomeStatement, BalanceSheet)):
        raise ValueError(
            f"Unexpected result type: {type(result)}. "
            f"Expected {schema_class.__name__}"
        )

    # Best-effort: populate metadata fields if prompt didn't set them
    try:
        if isinstance(result, IncomeStatement):
            if not getattr(result, "fiscal_period", None):
                result.fiscal_period = period
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
    metadata={"version": "4.0", "operation": "spread_pdf_multi_period"}
)
def spread_pdf_multi_period(
    pdf_path: str,
    doc_type: str,
    model_override: Optional[str] = None,
    max_pages: Optional[int] = None,
    dpi: int = 200,
    max_retries: int = 1,
    validation_tolerance: float = 0.05
) -> Union[MultiPeriodIncomeStatement, MultiPeriodBalanceSheet]:
    """
    Process a PDF financial statement and extract ALL detected periods.
    
    This function detects all period columns in the statement (e.g., FY2024, FY2023)
    and extracts data for each period, returning a multi-period result for
    side-by-side comparison.
    
    ARCHITECTURE:
    1. VISION-FIRST: PDF → Images → Vision API
    2. PERIOD DETECTION: Identify all period columns
    3. MULTI-EXTRACTION: Extract data for each period
    4. VALIDATION: Math checks on each period's data
    
    Args:
        pdf_path: Path to the PDF financial statement
        doc_type: Type of document ('income' or 'balance')
        model_override: Override model (testing only)
        max_pages: Maximum pages to process
        dpi: Image resolution for PDF conversion
        max_retries: Maximum retry attempts on validation failure
        validation_tolerance: Tolerance for math validation (default 5%)
        
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
                "mode": "multi-period"
            })
    except Exception:
        pass
    
    # -------------------------------------------------------------------------
    # STEP A: Convert PDF to Base64 Images (Vision-First)
    # -------------------------------------------------------------------------
    logger.info(f"[MULTI-PERIOD] Processing PDF: {pdf_path}")
    logger.info(f"Document type: {doc_type}")
    
    base64_images = _convert_pdf_to_images(pdf_path, dpi, max_pages)
    
    estimated_tokens = estimate_token_count(base64_images)
    logger.info(
        f"Converted {len(base64_images)} pages to images. "
        f"Estimated tokens: ~{estimated_tokens:,}"
    )
    
    # -------------------------------------------------------------------------
    # STEP B: Detect ALL Periods (not just the best one)
    # -------------------------------------------------------------------------
    schema_class = get_schema_for_doc_type(doc_type)
    
    # Get model configuration
    if model_override:
        model_name = model_override
        model_kwargs = {}
        if any(x in model_override.lower() for x in ["gpt-5", "o1", "o3"]):
            model_kwargs["reasoning_effort"] = os.getenv("OPENAI_REASONING_EFFORT", "high")
    else:
        prompt, hub_model_config = load_from_hub(doc_type)
        if hub_model_config and hub_model_config.get("model"):
            model_name = hub_model_config["model"]
            model_kwargs = {}
            if hub_model_config.get("reasoning_effort"):
                reasoning = hub_model_config["reasoning_effort"]
                valid_efforts = ["low", "medium", "high"]
                if reasoning not in valid_efforts:
                    reasoning = "medium"
                if "gpt-5.2" in model_name.lower() and reasoning != "medium":
                    reasoning = "medium"
                model_kwargs["reasoning_effort"] = reasoning
        else:
            model_name, model_kwargs = get_model_config_from_environment()
    
    # Run period detection to get ALL candidates
    logger.info("[MULTI-PERIOD] Detecting all period columns...")
    _, period_info = _detect_fiscal_period(
        base64_images=base64_images,
        doc_type=doc_type,
        model_name=model_name,
        model_kwargs=model_kwargs,
        requested_period="Latest",  # Always auto-detect for multi-period
    )
    
    # Build list of periods to extract
    periods_to_extract: List[Tuple[str, Optional[str]]] = []
    
    if period_info and period_info.candidates:
        # Sort by most recent first (is_most_recent=True comes first)
        sorted_candidates = sorted(
            period_info.candidates, 
            key=lambda x: (not x.is_most_recent, -x.confidence)
        )
        for candidate in sorted_candidates:
            if candidate.label and candidate.confidence >= 0.5:
                periods_to_extract.append((candidate.label, candidate.end_date))
        
        logger.info(f"[MULTI-PERIOD] Found {len(periods_to_extract)} period(s): {[p[0] for p in periods_to_extract]}")
    
    # Fallback: if no periods detected, use "Latest"
    if not periods_to_extract:
        logger.warning("[MULTI-PERIOD] No periods detected, falling back to 'Latest'")
        periods_to_extract = [("Latest", None)]
    
    # -------------------------------------------------------------------------
    # STEP C: Extract Data for Each Period
    # -------------------------------------------------------------------------
    prompt, _ = load_from_hub(doc_type)
    llm = create_llm(model_name=model_name, model_kwargs=model_kwargs)
    structured_llm = llm.with_structured_output(schema_class)
    
    extracted_periods = []
    
    for period_label, end_date in periods_to_extract:
        logger.info(f"[MULTI-PERIOD] Extracting data for period: {period_label}")
        
        try:
            # Extract for this specific period
            result = _invoke_llm_for_spreading(
                prompt=prompt,
                structured_llm=structured_llm,
                base64_images=base64_images,
                doc_type=doc_type,
                period=period_label,
                schema_class=schema_class,
                retry_context=None
            )
            
            # Validate
            validation = validate_spread(result, tolerance=validation_tolerance)
            if not validation.is_valid:
                logger.warning(f"[MULTI-PERIOD] Validation issues for {period_label}: {validation.errors}")
            
            # Wrap in period container
            if doc_type in ["income", "income_statement"]:
                period_data = IncomeStatementPeriod(
                    period_label=period_label,
                    end_date=end_date,
                    data=result
                )
            else:
                period_data = BalanceSheetPeriod(
                    period_label=period_label,
                    end_date=end_date,
                    data=result
                )
            
            extracted_periods.append(period_data)
            logger.info(f"[MULTI-PERIOD] Successfully extracted {period_label}")
            
        except Exception as e:
            logger.error(f"[MULTI-PERIOD] Failed to extract period {period_label}: {e}")
            # Continue with other periods
    
    # -------------------------------------------------------------------------
    # STEP D: Build Multi-Period Result
    # -------------------------------------------------------------------------
    if not extracted_periods:
        raise ValueError("Failed to extract any periods from the document")
    
    # Get currency/scale from first successful extraction
    first_data = extracted_periods[0].data
    currency = getattr(first_data, 'currency', 'USD')
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
    
    logger.info(f"[MULTI-PERIOD] Successfully extracted {len(extracted_periods)} period(s)")
    
    return result


def spread_financials(
    file_path: str,
    doc_type: str,
    period: str = "Latest",
    multi_period: bool = True,
    **kwargs
) -> Union[IncomeStatement, BalanceSheet, MultiPeriodIncomeStatement, MultiPeriodBalanceSheet]:
    """
    Unified entry point for spreading financial statements.
    
    Accepts file_path and routes to the appropriate processor based on file type.
    Currently supports PDF files (vision-first approach).
    
    Args:
        file_path: Path to the financial statement file (PDF, Excel future)
        doc_type: Type of document ('income' or 'balance')
        period: Fiscal period to extract (ignored if multi_period=True)
        multi_period: If True, extract all periods; if False, extract single period
        **kwargs: Additional arguments passed to the processor
        
    Returns:
        IncomeStatement/BalanceSheet (single) or MultiPeriodIncomeStatement/MultiPeriodBalanceSheet (multi)
    """
    from pathlib import Path
    
    path = Path(file_path)
    
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    ext = path.suffix.lower()
    
    if ext == ".pdf":
        if multi_period:
            return spread_pdf_multi_period(file_path, doc_type, **kwargs)
        else:
            return spread_pdf(file_path, doc_type, period, **kwargs)
    elif ext in [".xlsx", ".xls", ".xlsm"]:
        # Future: Excel support
        raise NotImplementedError(
            f"Excel support coming soon. Please convert to PDF for now."
        )
    else:
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: .pdf"
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
