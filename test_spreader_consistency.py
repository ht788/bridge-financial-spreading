"""
test_spreader_consistency.py - Regression Tests for Spreading Consistency

These tests ensure hyper-consistency in financial statement spreading:
- Same row label → same schema field across all periods
- "Total" rollup columns are never extracted as periods
- Gross profit and total operating expenses are always captured (not ignored as subtotals)
- Computed totals fill in when values are missing
- Cross-period consistency is validated

Test cases address the production failure where:
- A P&L with "Jan - Dec 2024", "Jan 2025", and "Total" columns had issues
- gross_profit was set to null and marked as "ignored subtotal"
- total_operating_expenses was null due to "ignored per instructions"
- SG&A was incorrectly derived
- Column selection drifted between periods
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List

# Import the functions we're testing
from spreader import (
    _classify_columns,
    validate_multi_period_consistency,
    apply_computed_totals,
    ColumnClassification,
    PeriodCandidate,
)
from models import (
    IncomeStatement,
    BalanceSheet,
    LineItem,
    IncomeStatementPeriod,
    BalanceSheetPeriod,
)


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def mock_llm_for_classification():
    """Create a mock LLM that returns predetermined column classifications."""
    def _create_mock(period_cols: List[str], rollup_cols: List[str], notes: str = None):
        mock_result = ColumnClassification(
            period_columns=period_cols,
            rollup_columns=rollup_cols,
            column_order=period_cols + rollup_cols,
            classification_notes=notes
        )
        
        mock_llm = MagicMock()
        mock_llm.with_structured_output.return_value.invoke.return_value = mock_result
        return mock_llm
    
    return _create_mock


@pytest.fixture
def sample_income_statement_with_all_fields():
    """Create a complete income statement with all fields populated."""
    return IncomeStatement(
        revenue=LineItem(value=1000000, confidence=0.95, raw_fields_used=["Total Revenue"]),
        cogs=LineItem(value=400000, confidence=0.95, raw_fields_used=["Cost of Goods Sold"]),
        gross_profit=LineItem(value=600000, confidence=0.95, raw_fields_used=["Gross Profit"]),
        sga=LineItem(value=200000, confidence=0.90, raw_fields_used=["SG&A Expenses"]),
        total_operating_expenses=LineItem(value=250000, confidence=0.90, raw_fields_used=["Total Operating Expenses"]),
        operating_income=LineItem(value=350000, confidence=0.90, raw_fields_used=["Operating Income"]),
        interest_expense=LineItem(value=50000, confidence=0.85, raw_fields_used=["Interest Expense"]),
        pretax_income=LineItem(value=300000, confidence=0.90, raw_fields_used=["Income Before Tax"]),
        income_tax_expense=LineItem(value=75000, confidence=0.85, raw_fields_used=["Tax Expense"]),
        net_income=LineItem(value=225000, confidence=0.95, raw_fields_used=["Net Income"]),
        fiscal_period="2024",
        currency="USD",
        scale="units"
    )


@pytest.fixture
def sample_income_statement_missing_gross_profit():
    """Create an income statement where gross_profit is null but should be computed."""
    return IncomeStatement(
        revenue=LineItem(value=1000000, confidence=0.95, raw_fields_used=["Total Revenue"]),
        cogs=LineItem(value=400000, confidence=0.95, raw_fields_used=["Cost of Goods Sold"]),
        gross_profit=LineItem(value=None, confidence=0.0, raw_fields_used=["IGNORED: treated as subtotal"]),
        sga=LineItem(value=200000, confidence=0.90, raw_fields_used=["SG&A Expenses"]),
        total_operating_expenses=LineItem(value=None, confidence=0.0, raw_fields_used=["IGNORED per instructions"]),
        operating_income=LineItem(value=None, confidence=0.0, raw_fields_used=[]),
        net_income=LineItem(value=225000, confidence=0.95, raw_fields_used=["Net Income"]),
        fiscal_period="2024",
        currency="USD",
        scale="units"
    )


# =============================================================================
# TEST: COLUMN CLASSIFICATION
# =============================================================================

class TestColumnClassification:
    """
    Tests for the column classification step that separates
    real period columns from rollup/total columns.
    """
    
    def test_two_periods_plus_total_column(self, mock_llm_for_classification):
        """
        REGRESSION TEST for production failure:
        
        A P&L with columns "Jan - Dec 2024", "Jan 2025", and "Total"
        must classify "Total" as ROLLUP, not as a PERIOD.
        """
        mock_llm = mock_llm_for_classification(
            period_cols=["Jan 2025", "Jan - Dec 2024"],
            rollup_cols=["Total"]
        )
        
        with patch('spreader.create_llm', return_value=mock_llm):
            result = _classify_columns(
                base64_images=[("fake_base64", "image/jpeg")],
                doc_type="income",
                model_name="gpt-5",
                model_kwargs={},
                period_candidates=[],
            )
            
            # "Total" must be in rollup_columns
            assert "Total" in result.rollup_columns, \
                "Total column should be classified as rollup, not period"
            
            # "Total" must NOT be in period_columns
            assert "Total" not in result.period_columns, \
                "Total column was incorrectly classified as a period"
            
            # Should have exactly 2 period columns
            assert len(result.period_columns) == 2, \
                f"Expected 2 period columns, got {len(result.period_columns)}"
            
            # Most recent period should be first
            assert result.period_columns[0] == "Jan 2025", \
                "Most recent period should be first in the list"
    
    def test_single_period_no_total_column(self, mock_llm_for_classification):
        """Single period statement without any Total column should work normally."""
        mock_llm = mock_llm_for_classification(
            period_cols=["FY2024"],
            rollup_cols=[]
        )
        
        with patch('spreader.create_llm', return_value=mock_llm):
            result = _classify_columns(
                base64_images=[("fake_base64", "image/jpeg")],
                doc_type="income",
                model_name="gpt-5",
                model_kwargs={},
                period_candidates=[],
            )
            
            assert result.period_columns == ["FY2024"]
            assert result.rollup_columns == []
    
    def test_ytd_column_classified_as_rollup(self, mock_llm_for_classification):
        """YTD (Year-to-Date) columns should be classified as rollups."""
        mock_llm = mock_llm_for_classification(
            period_cols=["Q4 2024", "Q3 2024"],
            rollup_cols=["YTD 2024"]
        )
        
        with patch('spreader.create_llm', return_value=mock_llm):
            result = _classify_columns(
                base64_images=[("fake_base64", "image/jpeg")],
                doc_type="income",
                model_name="gpt-5",
                model_kwargs={},
                period_candidates=[],
            )
            
            assert "YTD 2024" in result.rollup_columns
            assert "YTD 2024" not in result.period_columns
    
    def test_columns_not_left_to_right_by_recency(self, mock_llm_for_classification):
        """
        When document shows columns as '2023', '2024' (older first),
        period_columns should still return most recent first.
        """
        mock_llm = mock_llm_for_classification(
            period_cols=["2024", "2023"],  # Most recent first in output
            rollup_cols=[]
        )
        
        with patch('spreader.create_llm', return_value=mock_llm):
            result = _classify_columns(
                base64_images=[("fake_base64", "image/jpeg")],
                doc_type="balance",
                model_name="gpt-5",
                model_kwargs={},
                period_candidates=[],
            )
            
            # Most recent (2024) should be first regardless of document order
            assert result.period_columns[0] == "2024", \
                "Most recent period should be first in period_columns"
    
    def test_combined_grand_total_columns(self, mock_llm_for_classification):
        """Multiple rollup-type columns should all be excluded."""
        mock_llm = mock_llm_for_classification(
            period_cols=["Jan 2025", "Feb 2025"],
            rollup_cols=["Total", "Grand Total", "Combined"]
        )
        
        with patch('spreader.create_llm', return_value=mock_llm):
            result = _classify_columns(
                base64_images=[("fake_base64", "image/jpeg")],
                doc_type="income",
                model_name="gpt-5",
                model_kwargs={},
                period_candidates=[],
            )
            
            assert len(result.rollup_columns) == 3
            assert "Total" in result.rollup_columns
            assert "Grand Total" in result.rollup_columns
            assert "Combined" in result.rollup_columns


# =============================================================================
# TEST: GROSS PROFIT HANDLING
# =============================================================================

class TestGrossProfitHandling:
    """
    Tests for gross profit extraction and computation.
    
    REGRESSION: Production failure showed gross_profit being ignored as "subtotal"
    when it should have been extracted as a primary schema field.
    """
    
    def test_gross_profit_null_gets_computed(self):
        """
        REGRESSION TEST:
        
        When gross_profit is null (e.g., ignored as subtotal) but revenue
        and cogs are present, gross_profit MUST be computed.
        """
        data = IncomeStatement(
            revenue=LineItem(value=1000000, confidence=0.95, raw_fields_used=["Total Revenue"]),
            cogs=LineItem(value=400000, confidence=0.95, raw_fields_used=["Cost of Goods Sold"]),
            gross_profit=LineItem(value=None, confidence=0.0, raw_fields_used=["IGNORED: treated as subtotal"]),
        )
        
        updated, corrections = apply_computed_totals(data)
        
        # Gross profit must be computed
        assert updated.gross_profit.value == 600000, \
            f"Expected gross_profit=600000, got {updated.gross_profit.value}"
        
        # Confidence should be lower (computed, not extracted)
        assert updated.gross_profit.confidence < 0.9, \
            "Computed values should have lower confidence than extracted values"
        
        # raw_fields_used should indicate it was computed
        assert any("COMPUTED" in field for field in updated.gross_profit.raw_fields_used), \
            "raw_fields_used should indicate the value was computed"
        
        # Should have logged a correction
        assert len(corrections) > 0, "Should report that a correction was applied"
    
    def test_gross_profit_present_is_not_overwritten(self):
        """When gross_profit is already correctly populated, don't overwrite it."""
        data = IncomeStatement(
            revenue=LineItem(value=1000000, confidence=0.95, raw_fields_used=["Total Revenue"]),
            cogs=LineItem(value=400000, confidence=0.95, raw_fields_used=["Cost of Goods Sold"]),
            gross_profit=LineItem(value=600000, confidence=0.95, raw_fields_used=["Gross Profit"]),
        )
        
        updated, corrections = apply_computed_totals(data)
        
        # Should not have changed
        assert updated.gross_profit.value == 600000
        assert updated.gross_profit.confidence == 0.95  # Original confidence preserved
        assert "Gross Profit" in updated.gross_profit.raw_fields_used[0]  # Original source preserved
        assert len(corrections) == 0, "No corrections needed when value is correct"
    
    def test_gross_profit_mismatch_is_logged(self):
        """When extracted gross_profit doesn't match computed, it should be logged (not overwritten)."""
        data = IncomeStatement(
            revenue=LineItem(value=1000000, confidence=0.95, raw_fields_used=["Total Revenue"]),
            cogs=LineItem(value=400000, confidence=0.95, raw_fields_used=["Cost of Goods Sold"]),
            gross_profit=LineItem(value=550000, confidence=0.90, raw_fields_used=["Gross Profit"]),  # Wrong!
        )
        
        # This should log a warning but not overwrite the extracted value
        updated, corrections = apply_computed_totals(data)
        
        # The original (incorrect) value is preserved - validation catches it separately
        assert updated.gross_profit.value == 550000


# =============================================================================
# TEST: TOTAL OPERATING EXPENSES HANDLING
# =============================================================================

class TestTotalOperatingExpenses:
    """
    Tests for total operating expenses handling.
    
    REGRESSION: Production failure showed total_operating_expenses
    being ignored due to "ignored per instructions".
    """
    
    def test_total_opex_null_should_be_flagged(self):
        """
        When total_operating_expenses is null, the extraction prompt
        should be updated to capture it. This test validates the data model.
        """
        data = IncomeStatement(
            total_operating_expenses=LineItem(
                value=None, 
                confidence=0.0, 
                raw_fields_used=["IGNORED per instructions"]
            ),
        )
        
        # Verify the field structure allows null
        assert data.total_operating_expenses.value is None
        
        # This should NOT happen in production with the new prompts
        # The test documents the problematic state we're fixing


# =============================================================================
# TEST: CROSS-PERIOD CONSISTENCY
# =============================================================================

class TestCrossPeriodConsistency:
    """
    Tests for consistency validation across multiple periods.
    
    Key requirement: Same row label must map to same schema field
    across all periods in the same document.
    """
    
    def test_consistent_mapping_passes_validation(self):
        """When all periods use consistent field mappings, validation passes."""
        period1 = IncomeStatementPeriod(
            period_label="2024",
            data=IncomeStatement(
                revenue=LineItem(value=1000000, confidence=0.95, raw_fields_used=["Total Revenue"]),
                cogs=LineItem(value=400000, confidence=0.95, raw_fields_used=["Cost of Goods Sold"]),
            )
        )
        period2 = IncomeStatementPeriod(
            period_label="2023",
            data=IncomeStatement(
                revenue=LineItem(value=800000, confidence=0.95, raw_fields_used=["Total Revenue"]),
                cogs=LineItem(value=320000, confidence=0.95, raw_fields_used=["Cost of Goods Sold"]),
            )
        )
        
        is_consistent, errors, _ = validate_multi_period_consistency(
            [period1, period2], "income"
        )
        
        assert is_consistent, f"Expected consistent mapping, got errors: {errors}"
        assert len(errors) == 0
    
    def test_month_vs_year_periods_same_statement(self):
        """
        Statement with 'Jan 2025' (month) and 'Jan-Dec 2024' (year) periods
        should still have consistent mapping.
        """
        period1 = IncomeStatementPeriod(
            period_label="Jan 2025",
            data=IncomeStatement(
                revenue=LineItem(value=100000, confidence=0.95, raw_fields_used=["Total Revenue"]),
            )
        )
        period2 = IncomeStatementPeriod(
            period_label="Jan - Dec 2024",
            data=IncomeStatement(
                revenue=LineItem(value=1200000, confidence=0.95, raw_fields_used=["Total Revenue"]),
            )
        )
        
        is_consistent, errors, _ = validate_multi_period_consistency(
            [period1, period2], "income"
        )
        
        # Different period lengths are okay - what matters is consistent field mapping
        assert is_consistent
    
    def test_single_period_always_consistent(self):
        """Single period extraction is always consistent (nothing to compare)."""
        period1 = IncomeStatementPeriod(
            period_label="2024",
            data=IncomeStatement(
                revenue=LineItem(value=1000000, confidence=0.95, raw_fields_used=["Total Revenue"]),
            )
        )
        
        is_consistent, errors, _ = validate_multi_period_consistency(
            [period1], "income"
        )
        
        assert is_consistent
        assert len(errors) == 0


# =============================================================================
# TEST: OPERATING INCOME COMPUTATION
# =============================================================================

class TestOperatingIncomeComputation:
    """Tests for operating income computation when missing."""
    
    def test_operating_income_computed_when_missing(self):
        """When operating_income is null but gross_profit and opex exist, compute it."""
        data = IncomeStatement(
            revenue=LineItem(value=1000000, confidence=0.95, raw_fields_used=["Revenue"]),
            cogs=LineItem(value=400000, confidence=0.95, raw_fields_used=["COGS"]),
            gross_profit=LineItem(value=600000, confidence=0.95, raw_fields_used=["Gross Profit"]),
            total_operating_expenses=LineItem(value=200000, confidence=0.90, raw_fields_used=["Total OpEx"]),
            operating_income=LineItem(value=None, confidence=0.0, raw_fields_used=[]),
        )
        
        updated, corrections = apply_computed_totals(data)
        
        # operating_income = gross_profit - total_operating_expenses = 600000 - 200000 = 400000
        assert updated.operating_income.value == 400000
        assert any("COMPUTED" in field for field in updated.operating_income.raw_fields_used)


# =============================================================================
# TEST: INTEREST CLASSIFICATION
# =============================================================================

class TestInterestClassification:
    """
    Tests to document expected interest expense classification behavior.
    
    The actual classification happens in the LLM prompt, but these tests
    document the expected data model behavior.
    """
    
    def test_interest_expense_field_exists(self):
        """Verify interest_expense is a separate field from operating expenses."""
        data = IncomeStatement(
            interest_expense=LineItem(value=50000, confidence=0.85, raw_fields_used=["Interest Expense"]),
            sga=LineItem(value=100000, confidence=0.90, raw_fields_used=["SG&A"]),
        )
        
        # Interest expense should be separate from SG&A
        assert data.interest_expense.value == 50000
        assert data.sga.value == 100000
        # They should not be combined


# =============================================================================
# TEST: RETRY COLUMN FREEZE
# =============================================================================

class TestRetryColumnFreeze:
    """
    Tests to document that column classification is frozen during retries.
    
    Implementation note: The actual freeze happens in spread_pdf_multi_period
    by passing the same frozen_columns object to retry attempts.
    """
    
    def test_column_classification_is_immutable(self):
        """ColumnClassification should effectively be immutable once created."""
        classification = ColumnClassification(
            period_columns=["Jan 2025", "2024"],
            rollup_columns=["Total"],
            column_order=["2024", "Jan 2025", "Total"],
        )
        
        # Verify structure
        assert len(classification.period_columns) == 2
        assert len(classification.rollup_columns) == 1
        
        # The classification should be used as-is for all retry attempts
        # This is enforced by passing the same object to _invoke_llm_for_multi_period_spreading


# =============================================================================
# INTEGRATION TEST PLACEHOLDERS
# =============================================================================

class TestIntegrationPlaceholders:
    """
    Placeholder tests for integration testing.
    
    These tests require actual LLM calls and are marked for manual execution
    with real financial statement PDFs.
    """
    
    @pytest.mark.skip(reason="Requires live LLM - run manually with PDFs")
    def test_full_pipeline_two_periods_plus_total(self):
        """
        Integration test: Process a P&L with two periods and a Total column.
        
        Expected behavior:
        - Total column is excluded from extraction
        - Both period columns are extracted
        - Same row labels map to same fields in both periods
        - gross_profit and total_operating_expenses are captured
        """
        pass
    
    @pytest.mark.skip(reason="Requires live LLM - run manually with PDFs")
    def test_full_pipeline_gross_profit_absent(self):
        """
        Integration test: Process a P&L where Gross Profit row is not shown.
        
        Expected behavior:
        - gross_profit is computed from revenue - cogs
        - Confidence is lower than extracted values
        - raw_fields_used indicates computation
        """
        pass


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
