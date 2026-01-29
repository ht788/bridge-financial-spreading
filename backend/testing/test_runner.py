"""
Test Runner for Financial Spreader Evaluation

This module handles:
- Executing tests against example financials
- Comparing extractions to answer keys
- Calculating grades and scores
- Managing test history
"""

import os
import json
import re
import uuid
import logging
import time
import sqlite3
import traceback
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

# Import test models - try different import paths
try:
    from .test_models import (
        TestCompany, TestFile, TestRunConfig, TestRunResult,
        FileAnswerKey, PeriodAnswerKey, CompanyAnswerKey,
        FieldComparison, FieldAccuracy, PeriodGrade, FileGrade,
        GradeLevel, score_to_grade, TestRunSummary, TestHistoryResponse,
        ExpectedLineItem, AvailableModel, TestRunStatus
    )
except ImportError:
    from backend.testing.test_models import (
        TestCompany, TestFile, TestRunConfig, TestRunResult,
        FileAnswerKey, PeriodAnswerKey, CompanyAnswerKey,
        FieldComparison, FieldAccuracy, PeriodGrade, FileGrade,
        GradeLevel, score_to_grade, TestRunSummary, TestHistoryResponse,
        ExpectedLineItem, AvailableModel, TestRunStatus
    )

# Import spreader functionality
import sys
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from spreader import spread_financials, create_llm, load_from_hub, reset_fallback_flag, was_fallback_used
from models import MultiPeriodIncomeStatement, MultiPeriodBalanceSheet, CombinedFinancialExtraction
from model_config import export_for_api, get_all_models
from period_utils import (
    standardize_period_label,
    normalize_for_matching,
    periods_match,
    get_period_type
)

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION
# =============================================================================

EXAMPLE_FINANCIALS_DIR = Path(__file__).parent.parent.parent / "example_financials"
ANSWER_KEYS_DIR = Path(__file__).parent / "answer_keys"
TEST_HISTORY_DB = Path(__file__).parent / "test_history.db"

# Available models for testing - imported from centralized config
# This ensures consistency between regular app and testing lab
AVAILABLE_MODELS = export_for_api()

# Company definitions with their test files
TEST_COMPANIES: List[TestCompany] = [
    TestCompany(
        id="lkc",
        name="Lodging Kit Company",
        files=[
            # Income statements
            TestFile(filename="LKC 2022 Balance Sheet-combined.pdf", doc_type="income", period="2022", 
                     description="Combined file with Balance Sheet and P&L for 2022"),
            TestFile(filename="LKC 2023 PL Stmt.pdf", doc_type="income", period="2023"),
            TestFile(filename="LKC 2024 PL Stmt.pdf", doc_type="income", period="2024"),
            TestFile(filename="2025 YTD PL - LKC.pdf", doc_type="income", period="2025 YTD",
                     description="Year to date P&L through 3/27/25"),
            # Balance sheets
            TestFile(filename="LKC 2022 Balance Sheet-combined.pdf", doc_type="balance", period="2022",
                     description="Combined file with Balance Sheet and P&L for 2022"),
            TestFile(filename="LKC 2023 Balance Sheet.pdf", doc_type="balance", period="2023"),
            TestFile(filename="LKC 2024 Balance Sheet.pdf", doc_type="balance", period="2024"),
            TestFile(filename="2025 YTD Bal sh-LKC.pdf", doc_type="balance", period="2025 YTD",
                     description="Balance Sheet as of 3/27/25"),
        ],
        answer_key_path="lkc_answer_key.json"
    ),
    TestCompany(
        id="fomin",
        name="FOMIN LLC",
        files=[
            # Note: FOMIN P&L contains Jan-Dec 2024 and Jan 2025 columns
            TestFile(filename="FOMIN+LLC_Profit+and+Loss--.pdf", doc_type="income", period="2024-2025",
                     description="P&L covering Jan-Dec 2024 and Jan 2025"),
            TestFile(filename="FOMIN+LLC_Balance+Sheet--.pdf", doc_type="balance", period="Jan 2025",
                     description="Balance Sheet as of Jan 31, 2025 with comparatives"),
        ],
        answer_key_path="fomin_answer_key.json"
    ),
    TestCompany(
        id="pneo",
        name="pNeo LLC",
        files=[
            # Income statements
            TestFile(filename="FY_2023_pNeo_Financial_Packet.pdf", doc_type="income", period="2023",
                     description="FY2023 Financial Packet with Income Statement summary"),
            TestFile(filename="2024_Q4_pNeo_Consolidated_Financial_Reports.pdf", doc_type="income", period="2024",
                     description="Consolidated P&L for calendar year 2024"),
            # Balance sheets
            TestFile(filename="FY_2023_pNeo_Financial_Packet.pdf", doc_type="balance", period="2023",
                     description="FY2023 Financial Packet with Balance Sheet"),
            TestFile(filename="2024_Q4_pNeo_Consolidated_Financial_Reports.pdf", doc_type="balance", period="2024",
                     description="Consolidated Balance Sheet as of 12/31/24"),
        ],
        answer_key_path="pneo_answer_key.json"
    ),
    TestCompany(
        id="luminex",
        name="Candle-Lite (Luminex)",
        files=[
            # Annual Income Statements from PDFs
            TestFile(filename="Luminex/Luminex 2023 FS  - FINAL.pdf", doc_type="income", period="FY2023",
                     description="FY2023 audited financial statements with Income Statement"),
            TestFile(filename="Luminex/Luminex 2024 FS FINAL.pdf", doc_type="income", period="FY2024",
                     description="FY2024 audited financial statements with Income Statement"),
            TestFile(filename="Luminex/Luminex 2025 FS v2 6.24.pdf", doc_type="income", period="FY2025",
                     description="FY2025 audited financial statements with Income Statement"),
            # Annual Balance Sheets from PDFs
            TestFile(filename="Luminex/Luminex 2023 FS  - FINAL.pdf", doc_type="balance", period="FY2023",
                     description="FY2023 audited financial statements with Balance Sheet"),
            TestFile(filename="Luminex/Luminex 2024 FS FINAL.pdf", doc_type="balance", period="FY2024",
                     description="FY2024 audited financial statements with Balance Sheet"),
            TestFile(filename="Luminex/Luminex 2025 FS v2 6.24.pdf", doc_type="balance", period="FY2025",
                     description="FY2025 audited financial statements with Balance Sheet"),
            # Interim financials from Excel
            TestFile(filename="Luminex/2025-11-30 Candle-Lite Interim Financial Statements.xlsx", doc_type="income", period="FY2026 YTD",
                     description="Interim YTD Income Statement through Nov 30, 2025"),
            TestFile(filename="Luminex/2025-11-30 Candle-Lite Interim Financial Statements.xlsx", doc_type="balance", period="FY2026 YTD",
                     description="Interim Balance Sheet as of Nov 30, 2025"),
        ],
        answer_key_path="luminex_answer_key.json"
    )
]


def get_test_companies() -> List[TestCompany]:
    """Get list of available test companies with file availability info"""
    companies_with_status = []
    
    for company in TEST_COMPANIES:
        # Check which files actually exist
        available_files = []
        missing_files = []
        
        for test_file in company.files:
            file_path = EXAMPLE_FINANCIALS_DIR / test_file.filename
            if file_path.exists():
                available_files.append(test_file)
            else:
                missing_files.append(test_file)
        
        # Create a copy with availability metadata
        company_dict = company.model_dump()
        company_dict['available_files'] = len(available_files)
        company_dict['missing_files'] = len(missing_files)
        company_dict['files_available'] = [f.filename for f in available_files]
        company_dict['files_missing'] = [f.filename for f in missing_files]
        company_dict['can_test'] = len(available_files) > 0
        
        if missing_files:
            logger.warning(f"Company {company.id}: {len(missing_files)} test files missing")
        
        companies_with_status.append(TestCompany(**{k: v for k, v in company_dict.items() 
                                                    if k in TestCompany.model_fields}))
    
    return companies_with_status


def get_test_companies_status() -> List[Dict[str, Any]]:
    """Get detailed test company status including file availability"""
    companies_status = []
    
    for company in TEST_COMPANIES:
        available_files = []
        missing_files = []
        
        for test_file in company.files:
            file_path = EXAMPLE_FINANCIALS_DIR / test_file.filename
            file_info = {
                "filename": test_file.filename,
                "doc_type": test_file.doc_type,
                "period": test_file.period,
                "exists": file_path.exists()
            }
            if file_path.exists():
                file_info["size_bytes"] = file_path.stat().st_size
                available_files.append(file_info)
            else:
                missing_files.append(file_info)
        
        companies_status.append({
            "id": company.id,
            "name": company.name,
            "total_files": len(company.files),
            "available_files": len(available_files),
            "missing_files": len(missing_files),
            "can_test": len(available_files) > 0,
            "files": available_files + missing_files,
            "answer_key_path": company.answer_key_path
        })
    
    return companies_status


def get_available_models() -> List[AvailableModel]:
    """Get list of available models for testing"""
    # Convert exported API format to AvailableModel instances
    return [
        AvailableModel(
            id=m["id"],
            name=m["name"],
            description=m["description"]
        )
        for m in AVAILABLE_MODELS
    ]


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def parse_timestamp(ts_str: str) -> datetime:
    """Parse timestamp string from database, ensuring UTC timezone"""
    if ts_str.endswith('Z'):
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
    ts = datetime.fromisoformat(ts_str)
    if not ts.tzinfo:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def init_db():
    """Initialize SQLite database for test history"""
    ANSWER_KEYS_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(TEST_HISTORY_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_runs (
            id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            company_id TEXT NOT NULL,
            company_name TEXT NOT NULL,
            model_name TEXT NOT NULL,
            prompt_version TEXT,
            prompt_content TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            overall_score REAL NOT NULL,
            overall_grade TEXT NOT NULL,
            total_files INTEGER NOT NULL,
            total_periods INTEGER NOT NULL,
            total_fields_tested INTEGER NOT NULL,
            fields_correct INTEGER NOT NULL,
            fields_partial INTEGER NOT NULL,
            fields_wrong INTEGER NOT NULL,
            fields_missing INTEGER NOT NULL,
            execution_time_seconds REAL NOT NULL,
            error TEXT,
            results_json TEXT NOT NULL,
            metadata_json TEXT
        )
    ''')
    
    # Check if status column exists, add it if missing (migration)
    cursor.execute("PRAGMA table_info(test_runs)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'status' not in columns:
        logger.info("Migrating database: adding status column")
        cursor.execute("ALTER TABLE test_runs ADD COLUMN status TEXT NOT NULL DEFAULT 'complete'")
    
    conn.commit()
    conn.close()
    logger.info("Test history database initialized")


def save_test_result(result: TestRunResult):
    """Save a test result to the database"""
    init_db()
    
    conn = sqlite3.connect(TEST_HISTORY_DB)
    cursor = conn.cursor()
    
    # Use REPLACE to allow updating existing records
    cursor.execute('''
        INSERT OR REPLACE INTO test_runs (
            id, timestamp, company_id, company_name, model_name,
            prompt_version, prompt_content, status, overall_score, overall_grade,
            total_files, total_periods, total_fields_tested,
            fields_correct, fields_partial, fields_wrong, fields_missing,
            execution_time_seconds, error, results_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        result.id,
        result.timestamp.isoformat().replace('+00:00', 'Z') if result.timestamp.tzinfo else result.timestamp.isoformat() + "Z",
        result.company_id,
        result.company_name,
        result.model_name,
        result.prompt_version,
        result.prompt_content,
        result.status.value,
        result.overall_score,
        result.overall_grade.value,
        result.total_files,
        result.total_periods,
        result.total_fields_tested,
        result.fields_correct,
        result.fields_partial,
        result.fields_wrong,
        result.fields_missing,
        result.execution_time_seconds,
        result.error,
        json.dumps([f.model_dump() for f in result.file_results]),
        json.dumps(result.metadata)
    ))
    
    conn.commit()
    conn.close()
    logger.info(f"Saved test result {result.id} with status {result.status.value}")


def get_test_history(limit: int = 50, company_id: Optional[str] = None) -> TestHistoryResponse:
    """Get test history from database"""
    init_db()
    
    conn = sqlite3.connect(TEST_HISTORY_DB)
    cursor = conn.cursor()
    
    if company_id:
        cursor.execute('''
            SELECT id, timestamp, company_id, company_name, model_name,
                   prompt_version, status, overall_score, overall_grade, total_files,
                   execution_time_seconds
            FROM test_runs
            WHERE company_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (company_id, limit))
    else:
        cursor.execute('''
            SELECT id, timestamp, company_id, company_name, model_name,
                   prompt_version, status, overall_score, overall_grade, total_files,
                   execution_time_seconds
            FROM test_runs
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
    
    rows = cursor.fetchall()
    
    # Get total count
    if company_id:
        cursor.execute('SELECT COUNT(*) FROM test_runs WHERE company_id = ?', (company_id,))
    else:
        cursor.execute('SELECT COUNT(*) FROM test_runs')
    total_count = cursor.fetchone()[0]
    
    conn.close()
    
    runs = [
        TestRunSummary(
            id=row[0],
            timestamp=parse_timestamp(row[1]),
            company_id=row[2],
            company_name=row[3],
            model_name=row[4],
            prompt_version=row[5],
            status=TestRunStatus(row[6]) if row[6] else TestRunStatus.COMPLETE,
            overall_score=row[7],
            overall_grade=GradeLevel(row[8]),
            total_files=row[9],
            execution_time_seconds=row[10]
        )
        for row in rows
    ]
    
    return TestHistoryResponse(runs=runs, total_count=total_count)


def get_test_result_by_id(test_id: str) -> Optional[TestRunResult]:
    """Get a specific test result by ID"""
    init_db()
    
    conn = sqlite3.connect(TEST_HISTORY_DB)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, timestamp, company_id, company_name, model_name,
               prompt_version, prompt_content, status, overall_score, overall_grade,
               total_files, total_periods, total_fields_tested, fields_correct,
               fields_partial, fields_wrong, fields_missing, execution_time_seconds,
               error, results_json, metadata_json
        FROM test_runs WHERE id = ?
    ''', (test_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    # Parse the stored JSON
    file_results_data = json.loads(row[19]) if row[19] else []
    file_results = [FileGrade(**f) for f in file_results_data]
    
    # Parse metadata, handling both NULL and empty string
    metadata = {}
    if row[20] and row[20].strip():
        try:
            metadata = json.loads(row[20])
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse metadata JSON for test {test_id}, using empty dict")
            metadata = {}
    
    return TestRunResult(
        id=row[0],
        timestamp=parse_timestamp(row[1]),
        company_id=row[2],
        company_name=row[3],
        model_name=row[4],
        prompt_version=row[5],
        prompt_content=row[6],
        status=TestRunStatus(row[7]) if row[7] else TestRunStatus.COMPLETE,
        overall_score=row[8],
        overall_grade=GradeLevel(row[9]),
        total_files=row[10],
        total_periods=row[11],
        total_fields_tested=row[12],
        fields_correct=row[13],
        fields_partial=row[14],
        fields_wrong=row[15],
        fields_missing=row[16],
        execution_time_seconds=row[17],
        error=row[18],
        file_results=file_results,
        metadata=metadata
    )


# =============================================================================
# ANSWER KEY OPERATIONS
# =============================================================================

def load_answer_key(company_id: str) -> Optional[CompanyAnswerKey]:
    """Load answer key for a company"""
    company = next((c for c in TEST_COMPANIES if c.id == company_id), None)
    if not company or not company.answer_key_path:
        return None
    
    answer_key_file = ANSWER_KEYS_DIR / company.answer_key_path
    
    if not answer_key_file.exists():
        logger.warning(f"Answer key not found: {answer_key_file}")
        return None
    
    try:
        with open(answer_key_file, 'r') as f:
            data = json.load(f)
        return CompanyAnswerKey(**data)
    except Exception as e:
        logger.error(f"Failed to load answer key: {e}")
        return None


def save_answer_key(answer_key: CompanyAnswerKey):
    """Save answer key for a company"""
    ANSWER_KEYS_DIR.mkdir(parents=True, exist_ok=True)
    
    company = next((c for c in TEST_COMPANIES if c.id == answer_key.company_id), None)
    if not company:
        raise ValueError(f"Unknown company: {answer_key.company_id}")
    
    filename = company.answer_key_path or f"{answer_key.company_id}_answer_key.json"
    answer_key_file = ANSWER_KEYS_DIR / filename
    
    with open(answer_key_file, 'w') as f:
        json.dump(answer_key.model_dump(), f, indent=2)
    
    logger.info(f"Saved answer key: {answer_key_file}")


# =============================================================================
# GRADING LOGIC
# =============================================================================

def normalize_period_label(label: str) -> str:
    """
    Normalize a period label for fuzzy matching.
    
    Uses the central period_utils module for consistent normalization.
    """
    return normalize_for_matching(label)


def find_matching_period(
    extracted_label: str,
    answer_key_periods: List,
    fuzzy_match: bool = True
) -> Optional[Any]:
    """
    Find a matching period from the answer key for an extracted period label.
    
    Uses the improved periods_match function that handles:
    - "2023" matching "FY2023", "Jan-Dec 2023", "January through December 2023"
    - Quarter variations: "Q1 2024" matches "First Quarter 2024"
    - YTD variations: "YTD May 2025" matches "Jan-May 2025"
    
    Args:
        extracted_label: The period label from extraction
        answer_key_periods: List of PeriodAnswerKey objects
        fuzzy_match: Whether to use fuzzy matching (default True)
    
    Returns:
        The matching PeriodAnswerKey or None
    """
    if not extracted_label:
        return None
    
    # First try exact match
    for p in answer_key_periods:
        if p.period_label == extracted_label:
            logger.info(f"Exact match: '{extracted_label}' -> '{p.period_label}'")
            return p
    
    if not fuzzy_match:
        return None
    
    # Try the improved periods_match function
    for p in answer_key_periods:
        if periods_match(extracted_label, p.period_label):
            logger.info(f"Fuzzy match: '{extracted_label}' matched to answer key period '{p.period_label}'")
            return p
    
    # Log what we're trying to match for debugging
    logger.warning(
        f"No match found for period '{extracted_label}'. "
        f"Answer key has periods: {[p.period_label for p in answer_key_periods]}"
    )
    
    return None


def compare_field(
    field_name: str,
    extracted_value: Optional[float],
    expected: ExpectedLineItem,
    default_tolerance: float = 5.0
) -> FieldComparison:
    """
    Compare an extracted value against the expected value.
    
    Returns a FieldComparison with accuracy classification and score.
    """
    expected_value = expected.value
    tolerance = expected.tolerance_percent if expected.tolerance_percent else default_tolerance
    
    # Handle null/missing cases
    if expected_value is None:
        if extracted_value is None:
            return FieldComparison(
                field_name=field_name,
                expected_value=None,
                extracted_value=None,
                accuracy=FieldAccuracy.EXACT_MATCH,
                score=1.0,
                tolerance_used=tolerance,
                notes="Both null - correct"
            )
        else:
            # Extracted something when nothing expected
            return FieldComparison(
                field_name=field_name,
                expected_value=None,
                extracted_value=extracted_value,
                accuracy=FieldAccuracy.EXTRA,
                score=0.5,  # Not penalized heavily for extra data
                tolerance_used=tolerance,
                notes="Extracted value not in answer key"
            )
    
    if extracted_value is None:
        # Missing expected value
        return FieldComparison(
            field_name=field_name,
            expected_value=expected_value,
            extracted_value=None,
            accuracy=FieldAccuracy.MISSING,
            score=0.0,
            tolerance_used=tolerance,
            notes="Expected value not extracted"
        )
    
    # Both have values - compare them
    difference = abs(extracted_value - expected_value)
    
    # Handle zero expected value
    if expected_value == 0:
        if extracted_value == 0:
            difference_percent = 0
        else:
            difference_percent = 100  # Any non-zero when expecting zero
    else:
        difference_percent = (difference / abs(expected_value)) * 100
    
    # Determine accuracy level
    if difference == 0 or (expected_value != 0 and difference_percent < 0.01):
        accuracy = FieldAccuracy.EXACT_MATCH
        score = 1.0
        notes = "Exact match"
    elif difference_percent <= tolerance:
        accuracy = FieldAccuracy.WITHIN_TOLERANCE
        # Score scales from 1.0 at 0% diff to 0.8 at tolerance limit
        score = 1.0 - (difference_percent / tolerance) * 0.2
        notes = f"Within {tolerance}% tolerance"
    elif difference_percent <= tolerance * 2:
        accuracy = FieldAccuracy.PARTIAL
        # Score scales from 0.8 to 0.5
        score = 0.8 - ((difference_percent - tolerance) / tolerance) * 0.3
        notes = f"Partially correct ({difference_percent:.1f}% off)"
    else:
        # Check if sign is wrong (common error)
        if extracted_value * expected_value < 0:
            accuracy = FieldAccuracy.PARTIAL
            score = 0.3
            notes = "Sign appears to be wrong"
        else:
            accuracy = FieldAccuracy.WRONG
            score = 0.0
            notes = f"Significantly different ({difference_percent:.1f}% off)"
    
    return FieldComparison(
        field_name=field_name,
        expected_value=expected_value,
        extracted_value=extracted_value,
        accuracy=accuracy,
        score=score,
        tolerance_used=tolerance,
        difference=difference,
        difference_percent=difference_percent,
        notes=notes
    )


def grade_period(
    period_label: str,
    doc_type: str,
    extracted_data: Dict[str, Any],
    expected: Dict[str, ExpectedLineItem],
    default_tolerance: float = 5.0
) -> PeriodGrade:
    """Grade extraction results for a single period against answer key"""
    comparisons: List[FieldComparison] = []
    
    # Get all field names from both extracted and expected
    all_fields = set(expected.keys())
    
    for field_name in all_fields:
        expected_item = expected.get(field_name)
        if not expected_item:
            continue
        
        # Get extracted value
        extracted_field = extracted_data.get(field_name, {})
        extracted_value = None
        if isinstance(extracted_field, dict) and 'value' in extracted_field:
            extracted_value = extracted_field.get('value')
        
        comparison = compare_field(
            field_name=field_name,
            extracted_value=extracted_value,
            expected=expected_item,
            default_tolerance=default_tolerance
        )
        comparisons.append(comparison)
    
    # Calculate statistics
    total_fields = len(comparisons)
    matched = sum(1 for c in comparisons if c.accuracy == FieldAccuracy.EXACT_MATCH)
    partial = sum(1 for c in comparisons if c.accuracy in [FieldAccuracy.WITHIN_TOLERANCE, FieldAccuracy.PARTIAL])
    missing = sum(1 for c in comparisons if c.accuracy == FieldAccuracy.MISSING)
    wrong = sum(1 for c in comparisons if c.accuracy == FieldAccuracy.WRONG)
    extra = sum(1 for c in comparisons if c.accuracy == FieldAccuracy.EXTRA)
    
    # Calculate overall score (weighted average of field scores)
    if total_fields > 0:
        score = sum(c.score for c in comparisons) / total_fields * 100
    else:
        score = 100.0  # No fields to compare = perfect
    
    return PeriodGrade(
        period_label=period_label,
        doc_type=doc_type,
        total_fields=total_fields,
        matched_fields=matched,
        partial_fields=partial,
        missing_fields=missing,
        wrong_fields=wrong,
        extra_fields=extra,
        score=score,
        grade=score_to_grade(score),
        field_comparisons=comparisons
    )


# =============================================================================
# TEST EXECUTION
# =============================================================================

# Result type for file processing (used internally)
from dataclasses import dataclass, field as dataclass_field

@dataclass
class _FileProcessingResult:
    """Internal result type for parallel file processing"""
    file_idx: int
    test_file: TestFile
    success: bool
    file_grades: List[FileGrade] = dataclass_field(default_factory=list)
    total_periods: int = 0
    total_fields: int = 0
    fields_correct: int = 0
    fields_partial: int = 0
    fields_wrong: int = 0
    fields_missing: int = 0
    fallback_used: bool = False
    error: Optional[str] = None
    duration_seconds: float = 0.0


async def _process_test_file(
    test_id: str,
    file_idx: int,
    test_file: TestFile,
    file_path: Path,
    config: TestRunConfig,
    answer_key: Optional[CompanyAnswerKey],
    total_files: int,
    semaphore: asyncio.Semaphore,
    progress_callback=None,
    start_time: float = 0.0,
) -> _FileProcessingResult:
    """
    Process a single test file with semaphore-controlled concurrency.
    
    This helper function encapsulates the per-file logic for parallel execution.
    Uses asyncio.to_thread to run the synchronous spread_financials without blocking.
    
    Args:
        test_id: Unique ID for this test run
        file_idx: 1-based index of this file in the test
        test_file: The test file definition
        file_path: Full path to the file
        config: Test run configuration
        answer_key: Company answer key (optional)
        total_files: Total number of files in this test
        semaphore: Asyncio semaphore for concurrency control
        progress_callback: Optional async callback for progress updates
        start_time: Test start time for elapsed time calculation
    
    Returns:
        _FileProcessingResult with all grading data
    """
    result = _FileProcessingResult(
        file_idx=file_idx,
        test_file=test_file,
        success=False
    )
    
    async def emit_progress(phase: str, message: str, **kwargs):
        """Helper to emit progress updates"""
        if progress_callback:
            progress_data = {
                "phase": phase,
                "message": message,
                "elapsed_seconds": round(time.time() - start_time, 1) if start_time else 0,
                "test_id": test_id,
                **kwargs
            }
            try:
                await progress_callback(test_id, progress_data)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    # Acquire semaphore to limit concurrent extractions
    async with semaphore:
        logger.info(f"[TEST RUN {test_id}] " + "=" * 70)
        logger.info(f"[TEST RUN {test_id}] Processing file {file_idx}/{total_files}: {test_file.filename}")
        logger.info(f"[TEST RUN {test_id}] Doc Type: {test_file.doc_type}, Expected Period: {test_file.period}")
        logger.info(f"[TEST RUN {test_id}] File Path: {file_path}")
        
        # Emit progress for file start
        await emit_progress(
            "extracting",
            f"Processing {test_file.filename}...",
            total_files=total_files,
            current_file=file_idx,
            current_filename=test_file.filename,
            doc_type=test_file.doc_type,
            files_completed=0  # Will be updated by caller
        )
        
        if not file_path.exists():
            logger.error(f"[TEST RUN {test_id}] ❌ FILE NOT FOUND: {file_path}")
            result.error = f"File not found: {test_file.filename}"
            result.file_grades.append(FileGrade(
                filename=test_file.filename,
                doc_type=test_file.doc_type,
                periods=[],
                overall_score=0.0,
                overall_grade=GradeLevel.FAILING
            ))
            return result
        
        logger.info(f"[TEST RUN {test_id}] ✓ File exists, size: {file_path.stat().st_size} bytes")
        
        try:
            logger.info(f"[TEST RUN {test_id}] Calling spread_financials()...")
            logger.info(f"[TEST RUN {test_id}]   - file_path: {file_path}")
            logger.info(f"[TEST RUN {test_id}]   - doc_type: {test_file.doc_type}")
            logger.info(f"[TEST RUN {test_id}]   - multi_period: True")
            logger.info(f"[TEST RUN {test_id}]   - model_override: {config.model_name}")
            logger.info(f"[TEST RUN {test_id}]   - extended_thinking: {config.extended_thinking}")
            logger.info(f"[TEST RUN {test_id}]   - dpi: {config.dpi}")
            logger.info(f"[TEST RUN {test_id}]   - max_pages: {config.max_pages}")
            
            file_start = time.time()
            
            # Emit progress - starting LLM extraction
            await emit_progress(
                "extracting",
                f"Calling AI model to extract from {test_file.filename}...",
                total_files=total_files,
                current_file=file_idx,
                current_filename=test_file.filename,
                doc_type=test_file.doc_type,
                files_completed=0,
                sub_phase="llm_call"
            )
            
            # Reset fallback flag before processing
            reset_fallback_flag()
            
            # Run the spreader using asyncio.to_thread to prevent blocking
            extraction_result = await asyncio.to_thread(
                spread_financials,
                file_path=str(file_path),
                doc_type=test_file.doc_type,
                multi_period=True,
                model_override=config.model_name,
                extended_thinking=config.extended_thinking,
                dpi=config.dpi,
                max_pages=config.max_pages
            )
            
            result.duration_seconds = time.time() - file_start
            logger.info(f"[TEST RUN {test_id}] ✓ spread_financials() completed in {result.duration_seconds:.2f}s")
            
            # Emit progress - extraction complete, now grading
            await emit_progress(
                "grading",
                f"Grading extraction results for {test_file.filename}...",
                total_files=total_files,
                current_file=file_idx,
                current_filename=test_file.filename,
                doc_type=test_file.doc_type,
                files_completed=0,
                file_extraction_time=round(result.duration_seconds, 1)
            )
            
            # Check if fallback prompt was used
            if was_fallback_used():
                result.fallback_used = True
                logger.warning(f"[TEST RUN {test_id}] ⚠️ Fallback prompt was used for {test_file.filename}")
            
            # Handle combined extraction results (when doc_type='auto')
            if isinstance(extraction_result, CombinedFinancialExtraction):
                logger.info(f"[TEST RUN {test_id}] ✓ Received CombinedFinancialExtraction result")
                logger.info(f"[TEST RUN {test_id}]   - Has Income Statement: {extraction_result.detected_types.has_income_statement}")
                logger.info(f"[TEST RUN {test_id}]   - Has Balance Sheet: {extraction_result.detected_types.has_balance_sheet}")
                
                # Process each statement type that was detected
                statements_to_process = []
                if extraction_result.income_statement:
                    statements_to_process.append(('income', extraction_result.income_statement))
                if extraction_result.balance_sheet:
                    statements_to_process.append(('balance', extraction_result.balance_sheet))
                
                for stmt_doc_type, stmt_result in statements_to_process:
                    logger.info(f"[TEST RUN {test_id}] Processing {stmt_doc_type} statement from combined result...")
                    
                    # Get answer key for this doc type
                    file_answer_key = None
                    if answer_key:
                        file_answer_key = next(
                            (f for f in answer_key.files 
                             if f.filename == test_file.filename and f.doc_type == stmt_doc_type),
                            None
                        )
                        if file_answer_key:
                            logger.info(f"[TEST RUN {test_id}] Found answer key for {stmt_doc_type} with {len(file_answer_key.periods)} periods")
                    
                    # Grade each period
                    period_grades: List[PeriodGrade] = []
                    
                    if hasattr(stmt_result, 'periods'):
                        for period_idx, period in enumerate(stmt_result.periods, 1):
                            period_label = period.period_label
                            period_data = period.data.model_dump()
                            
                            logger.info(f"[TEST RUN {test_id}]   {stmt_doc_type.upper()} Period {period_idx}: '{period_label}'")
                            
                            # Get expected values for this period
                            expected = {}
                            if file_answer_key:
                                period_answer = find_matching_period(
                                    extracted_label=period_label,
                                    answer_key_periods=file_answer_key.periods,
                                    fuzzy_match=True
                                )
                                if period_answer:
                                    expected = {
                                        k: ExpectedLineItem(**v) if isinstance(v, dict) else v
                                        for k, v in period_answer.expected.items()
                                    }
                            
                            grade = grade_period(
                                period_label=period_label,
                                doc_type=stmt_doc_type,
                                extracted_data=period_data,
                                expected=expected,
                                default_tolerance=config.tolerance_percent
                            )
                            period_grades.append(grade)
                            logger.info(f"[TEST RUN {test_id}]   ✓ Period score: {grade.score:.1f}% ({grade.grade.value})")
                            
                            # Accumulate stats
                            result.total_periods += 1
                            result.total_fields += grade.total_fields
                            result.fields_correct += grade.matched_fields
                            result.fields_partial += grade.partial_fields
                            result.fields_wrong += grade.wrong_fields
                            result.fields_missing += grade.missing_fields
                    
                    # Calculate file-level score for this statement type
                    if period_grades:
                        file_score = sum(g.score for g in period_grades) / len(period_grades)
                    else:
                        file_score = 0.0
                    
                    file_grade = FileGrade(
                        filename=test_file.filename,
                        doc_type=stmt_doc_type,  # Use the actual statement type, not 'auto'
                        periods=period_grades,
                        overall_score=file_score,
                        overall_grade=score_to_grade(file_score)
                    )
                    result.file_grades.append(file_grade)
                    
                    logger.info(f"[TEST RUN {test_id}] ✓ {stmt_doc_type.upper()} processing complete: {file_score:.1f}%")
                
            else:
                # Standard single doc_type result (income or balance)
                # Get answer key for this file - match BOTH filename AND doc_type
                file_answer_key = None
                if answer_key:
                    file_answer_key = next(
                        (f for f in answer_key.files 
                         if f.filename == test_file.filename and f.doc_type == test_file.doc_type),
                        None
                    )
                    if file_answer_key:
                        logger.info(f"[TEST RUN {test_id}] Found answer key for {test_file.doc_type} with {len(file_answer_key.periods)} periods")
                        logger.info(f"[TEST RUN {test_id}] Answer key periods: {[p.period_label for p in file_answer_key.periods]}")
                    else:
                        # Try fallback to filename-only match for backwards compatibility
                        file_answer_key = next(
                            (f for f in answer_key.files if f.filename == test_file.filename),
                            None
                        )
                        if file_answer_key:
                            logger.warning(
                                f"[TEST RUN {test_id}] No exact doc_type match, using filename-only match "
                                f"(file doc_type: {file_answer_key.doc_type}, test doc_type: {test_file.doc_type})"
                            )
                        else:
                            logger.warning(f"[TEST RUN {test_id}] No answer key found for this file")
                
                # Grade each period
                period_grades: List[PeriodGrade] = []
                
                logger.info(f"[TEST RUN {test_id}] Checking result structure...")
                if hasattr(extraction_result, 'periods'):
                    logger.info(f"[TEST RUN {test_id}] ✓ Result has multi-period structure with {len(extraction_result.periods)} periods")
                    
                    for period_idx, period in enumerate(extraction_result.periods, 1):
                        period_label = period.period_label
                        period_data = period.data.model_dump()
                        
                        logger.info(f"[TEST RUN {test_id}]   Period {period_idx}/{len(extraction_result.periods)}: '{period_label}'")
                        logger.info(f"[TEST RUN {test_id}]     - Extracted fields: {len(period_data)}")
                        
                        # Get expected values for this period (using fuzzy matching)
                        expected = {}
                        if file_answer_key:
                            period_answer = find_matching_period(
                                extracted_label=period_label,
                                answer_key_periods=file_answer_key.periods,
                                fuzzy_match=True
                            )
                            if period_answer:
                                expected = {
                                    k: ExpectedLineItem(**v) if isinstance(v, dict) else v
                                    for k, v in period_answer.expected.items()
                                }
                                logger.info(f"[TEST RUN {test_id}]     - Matched to answer key period: '{period_answer.period_label}'")
                                logger.info(f"[TEST RUN {test_id}]     - Expected fields: {len(expected)}")
                            else:
                                logger.warning(f"[TEST RUN {test_id}]     - No expected values for period '{period_label}'")
                        
                        logger.info(f"[TEST RUN {test_id}]   Grading period '{period_label}'...")
                        grade = grade_period(
                            period_label=period_label,
                            doc_type=test_file.doc_type,
                            extracted_data=period_data,
                            expected=expected,
                            default_tolerance=config.tolerance_percent
                        )
                        period_grades.append(grade)
                        logger.info(f"[TEST RUN {test_id}]   ✓ Period score: {grade.score:.1f}% ({grade.grade.value})")
                        logger.info(f"[TEST RUN {test_id}]     - Matched: {grade.matched_fields}, Partial: {grade.partial_fields}, Wrong: {grade.wrong_fields}, Missing: {grade.missing_fields}")
                        
                        # Accumulate stats
                        result.total_periods += 1
                        result.total_fields += grade.total_fields
                        result.fields_correct += grade.matched_fields
                        result.fields_partial += grade.partial_fields
                        result.fields_wrong += grade.wrong_fields
                        result.fields_missing += grade.missing_fields
                else:
                    logger.warning(f"[TEST RUN {test_id}] ⚠️ Result does not have multi-period structure")
                
                # Calculate file-level score
                if period_grades:
                    file_score = sum(g.score for g in period_grades) / len(period_grades)
                    logger.info(f"[TEST RUN {test_id}] File overall score: {file_score:.1f}%")
                else:
                    file_score = 0.0
                    logger.warning(f"[TEST RUN {test_id}] No period grades - file score 0%")
                
                file_grade = FileGrade(
                    filename=test_file.filename,
                    doc_type=test_file.doc_type,
                    periods=period_grades,
                    overall_score=file_score,
                    overall_grade=score_to_grade(file_score)
                )
                result.file_grades.append(file_grade)
                
                logger.info(f"[TEST RUN {test_id}] ✓ File processing complete: {file_score:.1f}% ({file_grade.overall_grade.value})")
            
            result.success = True
            
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[TEST RUN {test_id}] ❌ Error processing {test_file.filename}:")
            logger.error(f"[TEST RUN {test_id}] {str(e)}")
            logger.error(f"[TEST RUN {test_id}] Traceback:\n{error_trace}")
            result.error = f"{test_file.filename}: {str(e)}"
            
            # Add failed file result
            result.file_grades.append(FileGrade(
                filename=test_file.filename,
                doc_type=test_file.doc_type,
                periods=[],
                overall_score=0.0,
                overall_grade=GradeLevel.FAILING
            ))
            
            logger.info(f"[TEST RUN {test_id}] Added failed result for {test_file.filename}")
    
    return result


async def run_test(config: TestRunConfig, progress_callback=None) -> TestRunResult:
    """
    Execute a full test run for a company.
    
    This will:
    1. Load the answer key for the company
    2. Run the spreader on each test file
    3. Compare results to answer key
    4. Calculate grades
    5. Save results to history
    
    Args:
        config: Test run configuration
        progress_callback: Optional async callback for progress updates.
                          Called with (test_id, progress_data) where progress_data contains:
                          - phase: current phase (loading, extracting, grading, complete)
                          - current_file: index of current file being processed (1-based)
                          - total_files: total number of files to process
                          - current_filename: name of current file
                          - current_period: index of current period (1-based)
                          - total_periods_in_file: periods in current file
                          - message: human-readable status message
                          - elapsed_seconds: time elapsed so far
                          - files_completed: number of files fully processed
    """
    start_time = time.time()
    test_id = str(uuid.uuid4())
    
    async def emit_progress(phase: str, message: str, **kwargs):
        """Helper to emit progress updates"""
        if progress_callback:
            progress_data = {
                "phase": phase,
                "message": message,
                "elapsed_seconds": round(time.time() - start_time, 1),
                "test_id": test_id,
                **kwargs
            }
            try:
                logger.info(f"[TEST RUN {test_id}] [PROGRESS] Emitting: {phase} - {message}")
                await progress_callback(test_id, progress_data)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    logger.info(f"=" * 80)
    logger.info(f"[TEST RUN {test_id}] Starting execution")
    logger.info(f"[TEST RUN {test_id}] Config: company_id={config.company_id}, model={config.model_name}")
    logger.info(f"=" * 80)
    
    # Get company info
    company = next((c for c in TEST_COMPANIES if c.id == config.company_id), None)
    if not company:
        logger.error(f"[TEST RUN {test_id}] Unknown company: {config.company_id}")
        raise ValueError(f"Unknown company: {config.company_id}")
    
    logger.info(f"[TEST RUN {test_id}] Found company: {company.name} ({len(company.files)} files)")
    logger.info(f"[TEST RUN {test_id}] Model: {config.model_name}")
    logger.info(f"[TEST RUN {test_id}] DPI: {config.dpi}, Max Pages: {config.max_pages}, Tolerance: {config.tolerance_percent}%")
    
    # Create initial test record with RUNNING status
    initial_result = TestRunResult(
        id=test_id,
        timestamp=datetime.now(timezone.utc),
        company_id=config.company_id,
        company_name=company.name,
        model_name=config.model_name,
        prompt_version=None,
        prompt_content=config.prompt_override,
        status=TestRunStatus.RUNNING,
        overall_score=0.0,
        overall_grade=GradeLevel.FAILING,
        file_results=[],
        total_files=len(company.files),
        total_periods=0,
        total_fields_tested=0,
        fields_correct=0,
        fields_partial=0,
        fields_wrong=0,
        fields_missing=0,
        execution_time_seconds=0.0,
        error=None,
        metadata={
            "dpi": config.dpi,
            "max_pages": config.max_pages,
            "tolerance_percent": config.tolerance_percent,
            "parallel": config.parallel,
            "max_concurrent": config.max_concurrent
        }
    )
    
    # Save initial state to database
    logger.info(f"[TEST RUN {test_id}] Saving initial test state to database...")
    try:
        save_test_result(initial_result)
        logger.info(f"[TEST RUN {test_id}] ✓ Initial state saved with RUNNING status")
    except Exception as e:
        logger.error(f"[TEST RUN {test_id}] ❌ Failed to save initial state: {e}")
        logger.error(traceback.format_exc())
    
    # Emit initial progress
    await emit_progress(
        "initializing",
        f"Initializing test for {company.name}...",
        total_files=len(company.files),
        current_file=0,
        files_completed=0,
        company_name=company.name,
        model_name=config.model_name
    )
    
    # Load answer key
    logger.info(f"[TEST RUN {test_id}] Loading answer key for {config.company_id}...")
    await emit_progress(
        "loading",
        "Loading answer key...",
        total_files=len(company.files),
        current_file=0,
        files_completed=0
    )
    
    answer_key = load_answer_key(config.company_id)
    if not answer_key:
        logger.warning(f"[TEST RUN {test_id}] No answer key found for {config.company_id}, will compare against extracted data only")
    else:
        logger.info(f"[TEST RUN {test_id}] Answer key loaded: {len(answer_key.files)} files with expected results")
    
    # Track results
    file_results: List[FileGrade] = []
    total_score = 0.0
    total_files = 0
    total_periods = 0
    total_fields = 0
    fields_correct = 0
    fields_partial = 0
    fields_wrong = 0
    fields_missing = 0
    errors = []
    fallback_used_in_test = False  # Track if any file used fallback
    
    files_completed = 0
    
    # Log parallel processing configuration
    processing_mode = "parallel" if config.parallel else "sequential"
    logger.info(f"[TEST RUN {test_id}] Processing mode: {processing_mode}")
    if config.parallel:
        logger.info(f"[TEST RUN {test_id}] Max concurrent extractions: {config.max_concurrent}")
    
    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(config.max_concurrent if config.parallel else 1)
    
    # Emit progress for processing start
    await emit_progress(
        "extracting",
        f"Starting {processing_mode} extraction of {len(company.files)} files...",
        total_files=len(company.files),
        current_file=0,
        files_completed=0,
        parallel=config.parallel,
        max_concurrent=config.max_concurrent
    )
    
    if config.parallel:
        # PARALLEL PROCESSING: Create tasks for all files and run with asyncio.gather
        logger.info(f"[TEST RUN {test_id}] Creating parallel tasks for {len(company.files)} files...")
        
        tasks = []
        for file_idx, test_file in enumerate(company.files, 1):
            file_path = EXAMPLE_FINANCIALS_DIR / test_file.filename
            
            task = _process_test_file(
                test_id=test_id,
                file_idx=file_idx,
                test_file=test_file,
                file_path=file_path,
                config=config,
                answer_key=answer_key,
                total_files=len(company.files),
                semaphore=semaphore,
                progress_callback=progress_callback,
                start_time=start_time
            )
            tasks.append(task)
        
        # Execute all tasks in parallel (with semaphore limiting concurrent extractions)
        logger.info(f"[TEST RUN {test_id}] Executing {len(tasks)} tasks in parallel (max_concurrent={config.max_concurrent})...")
        processing_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results from all tasks
        for proc_result in processing_results:
            if isinstance(proc_result, Exception):
                # Handle unexpected exceptions from gather
                logger.error(f"[TEST RUN {test_id}] Unexpected exception in parallel task: {proc_result}")
                errors.append(f"Unexpected error: {str(proc_result)}")
                continue
            
            # Aggregate results from the file processing result
            for file_grade in proc_result.file_grades:
                file_results.append(file_grade)
                total_score += file_grade.overall_score
                total_files += 1
            
            total_periods += proc_result.total_periods
            total_fields += proc_result.total_fields
            fields_correct += proc_result.fields_correct
            fields_partial += proc_result.fields_partial
            fields_wrong += proc_result.fields_wrong
            fields_missing += proc_result.fields_missing
            
            if proc_result.fallback_used:
                fallback_used_in_test = True
            
            if proc_result.error:
                errors.append(proc_result.error)
            
            files_completed += 1
            
            # Emit progress for completed file
            if proc_result.file_grades:
                avg_score = sum(fg.overall_score for fg in proc_result.file_grades) / len(proc_result.file_grades)
                await emit_progress(
                    "file_complete",
                    f"Completed {proc_result.test_file.filename}: {avg_score:.1f}%",
                    total_files=len(company.files),
                    current_file=proc_result.file_idx,
                    current_filename=proc_result.test_file.filename,
                    files_completed=files_completed,
                    file_score=round(avg_score, 1),
                    file_grade=proc_result.file_grades[0].overall_grade.value if proc_result.file_grades else 'F'
                )
    
    else:
        # SEQUENTIAL PROCESSING: Process files one at a time (original behavior)
        logger.info(f"[TEST RUN {test_id}] Processing {len(company.files)} files sequentially...")
        
        for file_idx, test_file in enumerate(company.files, 1):
            file_path = EXAMPLE_FINANCIALS_DIR / test_file.filename
            
            proc_result = await _process_test_file(
                test_id=test_id,
                file_idx=file_idx,
                test_file=test_file,
                file_path=file_path,
                config=config,
                answer_key=answer_key,
                total_files=len(company.files),
                semaphore=semaphore,
                progress_callback=progress_callback,
                start_time=start_time
            )
            
            # Aggregate results from the file processing result
            for file_grade in proc_result.file_grades:
                file_results.append(file_grade)
                total_score += file_grade.overall_score
                total_files += 1
            
            total_periods += proc_result.total_periods
            total_fields += proc_result.total_fields
            fields_correct += proc_result.fields_correct
            fields_partial += proc_result.fields_partial
            fields_wrong += proc_result.fields_wrong
            fields_missing += proc_result.fields_missing
            
            if proc_result.fallback_used:
                fallback_used_in_test = True
            
            if proc_result.error:
                errors.append(proc_result.error)
            
            files_completed += 1
            
            # Emit progress for completed file
            if proc_result.file_grades:
                avg_score = sum(fg.overall_score for fg in proc_result.file_grades) / len(proc_result.file_grades)
                await emit_progress(
                    "file_complete",
                    f"Completed {test_file.filename}: {avg_score:.1f}%",
                    total_files=len(company.files),
                    current_file=file_idx,
                    current_filename=test_file.filename,
                    files_completed=files_completed,
                    file_score=round(avg_score, 1),
                    file_grade=proc_result.file_grades[0].overall_grade.value if proc_result.file_grades else 'F'
                )
            elif proc_result.error:
                await emit_progress(
                    "file_error",
                    f"Error processing {test_file.filename}: {proc_result.error[:100]}",
                    total_files=len(company.files),
                    current_file=file_idx,
                    current_filename=test_file.filename,
                    files_completed=files_completed,
                    error=proc_result.error[:200]
                )
    
    # Calculate overall score
    logger.info(f"[TEST RUN {test_id}] " + "=" * 70)
    logger.info(f"[TEST RUN {test_id}] CALCULATING FINAL RESULTS")
    logger.info(f"[TEST RUN {test_id}]   Total files processed: {total_files}")
    logger.info(f"[TEST RUN {test_id}]   Total periods graded: {total_periods}")
    logger.info(f"[TEST RUN {test_id}]   Total fields tested: {total_fields}")
    logger.info(f"[TEST RUN {test_id}]   Cumulative score: {total_score:.2f}")
    
    if total_files > 0:
        overall_score = total_score / total_files
        logger.info(f"[TEST RUN {test_id}]   Overall score: {overall_score:.2f}%")
    else:
        overall_score = 0.0
        logger.error(f"[TEST RUN {test_id}]   No files processed - overall score: 0%")
    
    execution_time = time.time() - start_time
    logger.info(f"[TEST RUN {test_id}]   Execution time: {execution_time:.2f}s")
    
    if errors:
        logger.error(f"[TEST RUN {test_id}]   Errors encountered: {len(errors)}")
        for err in errors:
            logger.error(f"[TEST RUN {test_id}]     - {err}")
    
    # Build result
    logger.info(f"[TEST RUN {test_id}] Building TestRunResult object...")
    result = TestRunResult(
        id=test_id,
        timestamp=datetime.now(timezone.utc),
        company_id=config.company_id,
        company_name=company.name,
        model_name=config.model_name,
        prompt_version=None,  # TODO: Get from Hub
        prompt_content=config.prompt_override,
        status=TestRunStatus.COMPLETE if not errors else TestRunStatus.ERROR,
        overall_score=overall_score,
        overall_grade=score_to_grade(overall_score),
        file_results=file_results,
        total_files=total_files,
        total_periods=total_periods,
        total_fields_tested=total_fields,
        fields_correct=fields_correct,
        fields_partial=fields_partial,
        fields_wrong=fields_wrong,
        fields_missing=fields_missing,
        execution_time_seconds=execution_time,
        error="; ".join(errors) if errors else None,
        fallback_prompt_used=fallback_used_in_test,
        metadata={
            "dpi": config.dpi,
            "max_pages": config.max_pages,
            "tolerance_percent": config.tolerance_percent,
            "parallel": config.parallel,
            "max_concurrent": config.max_concurrent
        }
    )
    
    # Save to database
    logger.info(f"[TEST RUN {test_id}] Saving final result to database...")
    try:
        save_test_result(result)
        logger.info(f"[TEST RUN {test_id}] ✓ Result saved to database with status {result.status.value}")
    except Exception as e:
        logger.error(f"[TEST RUN {test_id}] ❌ Failed to save to database: {e}")
        logger.error(traceback.format_exc())
    
    logger.info(f"=" * 80)
    logger.info(
        f"[TEST RUN {test_id}] ✓ COMPLETE: {overall_score:.1f}% ({result.overall_grade.value}) "
        f"in {execution_time:.1f}s"
    )
    logger.info(f"=" * 80)
    
    # Emit final completion progress
    await emit_progress(
        "complete",
        f"Test complete: {overall_score:.1f}% ({result.overall_grade.value})",
        total_files=total_files,
        files_completed=total_files,
        overall_score=round(overall_score, 1),
        overall_grade=result.overall_grade.value,
        total_periods=total_periods,
        fields_correct=fields_correct,
        fields_wrong=fields_wrong,
        fields_missing=fields_missing
    )
    
    return result


def get_current_prompt_content(doc_type: str = "income") -> Optional[str]:
    """Get the current prompt content from LangSmith Hub"""
    try:
        prompt, _ = load_from_hub(doc_type)
        if prompt and hasattr(prompt, 'messages') and prompt.messages:
            for msg in prompt.messages:
                if hasattr(msg, 'prompt') and hasattr(msg.prompt, 'template'):
                    return msg.prompt.template
        return None
    except Exception as e:
        logger.error(f"Failed to get prompt content: {e}")
        return None
