"""
Test script to verify in-progress test tracking functionality.

This script tests:
1. Database schema migration
2. Initial test creation with RUNNING status
3. Test completion with COMPLETE status
4. History retrieval including status
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from backend.testing.test_runner import (
    init_db, save_test_result, get_test_history,
    get_test_result_by_id, TEST_HISTORY_DB
)
from backend.testing.test_models import (
    TestRunResult, TestRunStatus, GradeLevel,
    TestRunConfig
)
from datetime import datetime, timezone
import uuid
import sqlite3


def test_database_migration():
    """Test that the status column is properly added"""
    print("=" * 70)
    print("TEST 1: Database Migration")
    print("=" * 70)
    
    # Initialize database (should create/migrate schema)
    init_db()
    
    # Check that status column exists
    conn = sqlite3.connect(TEST_HISTORY_DB)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(test_runs)")
    columns = [column[1] for column in cursor.fetchall()]
    conn.close()
    
    assert 'status' in columns, "[FAIL] Status column not found in database"
    print("[PASS] Status column exists in database schema")
    print()


def test_save_and_retrieve_running_test():
    """Test saving a test with RUNNING status"""
    print("=" * 70)
    print("TEST 2: Save and Retrieve Running Test")
    print("=" * 70)
    
    test_id = str(uuid.uuid4())
    
    # Create a test result with RUNNING status
    test_result = TestRunResult(
        id=test_id,
        timestamp=datetime.now(timezone.utc),
        company_id="test_company",
        company_name="Test Company",
        model_name="test-model",
        status=TestRunStatus.RUNNING,
        overall_score=0.0,
        overall_grade=GradeLevel.FAILING,
        file_results=[],
        total_files=5,
        execution_time_seconds=0.0
    )
    
    # Save to database
    save_test_result(test_result)
    print(f"[PASS] Saved test {test_id} with RUNNING status")
    
    # Retrieve from database
    retrieved = get_test_result_by_id(test_id)
    
    assert retrieved is not None, f"[FAIL] Failed to retrieve test {test_id}"
    assert retrieved.status == TestRunStatus.RUNNING, f"[FAIL] Expected RUNNING status, got {retrieved.status}"
    assert retrieved.id == test_id, "[FAIL] Test ID mismatch"
    
    print(f"[PASS] Retrieved test with status: {retrieved.status.value}")
    print()
    
    return test_id


def test_update_test_to_complete(test_id: str):
    """Test updating a running test to complete"""
    print("=" * 70)
    print("TEST 3: Update Test to Complete")
    print("=" * 70)
    
    # Retrieve the running test
    test_result = get_test_result_by_id(test_id)
    assert test_result is not None, "[FAIL] Test not found"
    
    # Update to complete
    test_result.status = TestRunStatus.COMPLETE
    test_result.overall_score = 95.5
    test_result.overall_grade = GradeLevel.PERFECT
    test_result.execution_time_seconds = 120.5
    
    # Save updated result
    save_test_result(test_result)
    print(f"[PASS] Updated test {test_id} to COMPLETE status")
    
    # Retrieve again
    updated = get_test_result_by_id(test_id)
    assert updated.status == TestRunStatus.COMPLETE, f"[FAIL] Expected COMPLETE, got {updated.status}"
    assert updated.overall_score == 95.5, "[FAIL] Score mismatch"
    
    print(f"[PASS] Verified update: status={updated.status.value}, score={updated.overall_score}")
    print()


def test_history_includes_status():
    """Test that history includes status field"""
    print("=" * 70)
    print("TEST 4: History Includes Status")
    print("=" * 70)
    
    # Get history
    history = get_test_history(limit=10)
    
    print(f"[PASS] Retrieved {len(history.runs)} test runs")
    
    if len(history.runs) > 0:
        for run in history.runs[:5]:  # Show first 5
            print(f"  - {run.id[:8]}... | {run.company_name} | Status: {run.status.value} | Score: {run.overall_score:.1f}%")
    
    print()


def test_create_multiple_status_tests():
    """Create tests with various statuses for visualization"""
    print("=" * 70)
    print("TEST 5: Create Multiple Status Tests")
    print("=" * 70)
    
    statuses = [
        (TestRunStatus.PENDING, "pending_test"),
        (TestRunStatus.RUNNING, "running_test"),
        (TestRunStatus.COMPLETE, "complete_test"),
        (TestRunStatus.ERROR, "error_test"),
    ]
    
    for status, name_prefix in statuses:
        test_id = str(uuid.uuid4())
        
        test_result = TestRunResult(
            id=test_id,
            timestamp=datetime.now(timezone.utc),
            company_id="demo",
            company_name=f"Demo - {status.value.title()}",
            model_name="demo-model",
            status=status,
            overall_score=85.0 if status == TestRunStatus.COMPLETE else 0.0,
            overall_grade=GradeLevel.GOOD if status == TestRunStatus.COMPLETE else GradeLevel.FAILING,
            file_results=[],
            total_files=3,
            execution_time_seconds=60.0 if status in [TestRunStatus.COMPLETE, TestRunStatus.ERROR] else 0.0,
            error="Test error message" if status == TestRunStatus.ERROR else None
        )
        
        save_test_result(test_result)
        print(f"[PASS] Created {status.value} test: {test_id[:8]}...")
    
    print()


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("IN-PROGRESS TEST TRACKING - VERIFICATION TESTS")
    print("=" * 70)
    print()
    
    try:
        # Run tests in sequence
        test_database_migration()
        test_id = test_save_and_retrieve_running_test()
        test_update_test_to_complete(test_id)
        test_history_includes_status()
        test_create_multiple_status_tests()
        
        print("=" * 70)
        print("ALL TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  - Database schema includes 'status' column")
        print("  - Can save tests with RUNNING status")
        print("  - Can update tests from RUNNING to COMPLETE")
        print("  - History includes status information")
        print("  - All status types work correctly")
        print()
        print("Next steps:")
        print("  1. Start the backend server")
        print("  2. Open the Testing Lab in the UI")
        print("  3. Run a test and watch it appear in history immediately")
        print("  4. Observe the status change from 'Running' to 'Complete'")
        print()
        
    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
