"""
Period Utilities - Standardization and Matching for Financial Periods

This module provides consistent period labeling and fuzzy matching for:
- Fiscal Years: FY23, FY24
- Quarters: Q123, Q223, Q324 (Q1 2023, Q2 2023, Q3 2024)
- Interim/YTD periods: YTD-May-2025, YTD-Mar-2024

Standard formats:
- Full fiscal years: FY23 (two-digit year)
- Quarters: Q123 (Q + quarter number + two-digit year)
- YTD/Interim: YTD-{Month}-{FullYear}
"""

import re
from typing import Optional, Tuple
from datetime import datetime

# Month abbreviations for standardization
MONTH_MAP = {
    'january': 'Jan', 'jan': 'Jan',
    'february': 'Feb', 'feb': 'Feb',
    'march': 'Mar', 'mar': 'Mar',
    'april': 'Apr', 'apr': 'Apr',
    'may': 'May',
    'june': 'Jun', 'jun': 'Jun',
    'july': 'Jul', 'jul': 'Jul',
    'august': 'Aug', 'aug': 'Aug',
    'september': 'Sep', 'sep': 'Sep', 'sept': 'Sep',
    'october': 'Oct', 'oct': 'Oct',
    'november': 'Nov', 'nov': 'Nov',
    'december': 'Dec', 'dec': 'Dec'
}

MONTH_ORDER = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

# Month to quarter mapping (fiscal year ending December)
MONTH_TO_QUARTER = {
    'Jan': 1, 'Feb': 1, 'Mar': 1,
    'Apr': 2, 'May': 2, 'Jun': 2,
    'Jul': 3, 'Aug': 3, 'Sep': 3,
    'Oct': 4, 'Nov': 4, 'Dec': 4
}


def _extract_year(text: str) -> Optional[int]:
    """Extract a year from text (4-digit or 2-digit with inference)."""
    # First try 4-digit year
    match = re.search(r'(19|20)\d{2}', text)
    if match:
        return int(match.group())
    
    # Try 2-digit year with apostrophe (e.g., '24, '23)
    match = re.search(r"['`'](\d{2})\b", text)
    if match:
        year_short = int(match.group(1))
        # Assume 2000s for years < 50, 1900s for years >= 50
        return 2000 + year_short if year_short < 50 else 1900 + year_short
    
    # Try standalone 2-digit year after FY (e.g., FY24)
    match = re.search(r'fy\s*(\d{2})\b', text.lower())
    if match:
        year_short = int(match.group(1))
        return 2000 + year_short if year_short < 50 else 1900 + year_short
    
    return None


def _extract_two_digit_year(text: str) -> Optional[str]:
    """Extract year and return as 2-digit string."""
    year = _extract_year(text)
    if year:
        return str(year)[-2:]
    return None


def _normalize_month(text: str) -> Optional[str]:
    """Normalize month name to standard 3-letter abbreviation."""
    text_lower = text.lower().strip()
    for key, value in MONTH_MAP.items():
        if key in text_lower:
            return value
    return None


def _detect_full_year_period(text: str) -> bool:
    """
    Detect if a period label represents a full fiscal year.
    
    Returns True for patterns like:
    - "2024", "2023"
    - "FY2024", "FY 2024", "FY24"
    - "Year Ended December 31, 2024"
    - "January through December 2024"
    - "Jan - Dec 2024", "Jan-Dec 2024"
    - "12 months ended..."
    """
    text_lower = text.lower().strip()
    
    # Pattern 1: Just a year
    if re.match(r'^(fy\s?)?\d{2,4}$', text_lower):
        return True
    
    # Pattern 2: FY prefix variations
    if re.match(r'^fy\s*\d{2,4}', text_lower):
        return True
    
    # Pattern 3: "Year ended" phrases
    if 'year ended' in text_lower or 'year ending' in text_lower:
        return True
    
    # Pattern 4: Full month range covering Jan-Dec
    # Matches: "January through December", "Jan - Dec", "Jan-Dec"
    jan_dec_pattern = r'(january|jan)\s*[-–—to\s]+(december|dec)'
    if re.search(jan_dec_pattern, text_lower):
        return True
    
    # Pattern 5: "12 months ended" or similar
    if re.search(r'(12|twelve)\s*months?\s*(ended|ending)', text_lower):
        return True
    
    # Pattern 6: Full date range "01/01/2024 - 12/31/2024"
    if re.search(r'(01|1)[/\-](01|1)[/\-]\d{4}\s*[-–—to]+\s*(12)[/\-](31)[/\-]\d{4}', text_lower):
        return True
    
    return False


def _detect_quarter_period(text: str) -> Optional[Tuple[int, int]]:
    """
    Detect if a period label represents a quarter.
    
    Returns (quarter_number, year) or None.
    
    Patterns detected:
    - "Q1 2024", "Q3 '24", "Q4-2024"
    - "Three months ended March 31, 2024" (Q1)
    - "Three months ended June 30, 2024" (Q2)
    - "First Quarter 2024", "Second Quarter 2024"
    """
    text_lower = text.lower().strip()
    year = _extract_year(text)
    
    if not year:
        return None
    
    # Pattern 1: Q# format
    match = re.search(r'q\s*([1-4])', text_lower)
    if match:
        return int(match.group(1)), year
    
    # Pattern 2: Ordinal quarter
    quarter_ordinals = {
        'first': 1, '1st': 1,
        'second': 2, '2nd': 2,
        'third': 3, '3rd': 3,
        'fourth': 4, '4th': 4
    }
    for ordinal, qnum in quarter_ordinals.items():
        if ordinal in text_lower and 'quarter' in text_lower:
            return qnum, year
    
    # Pattern 3: "Three months ended [date]"
    if 'three months' in text_lower or '3 months' in text_lower:
        # Check for quarter-ending months
        if 'march' in text_lower or 'mar' in text_lower:
            return 1, year
        elif 'june' in text_lower or 'jun' in text_lower:
            return 2, year
        elif 'september' in text_lower or 'sep' in text_lower:
            return 3, year
        elif 'december' in text_lower or 'dec' in text_lower:
            return 4, year
    
    return None


def _detect_ytd_period(text: str) -> Optional[Tuple[str, int]]:
    """
    Detect if a period label represents a Year-to-Date period.
    
    Returns (month_abbrev, year) or None.
    
    Patterns detected:
    - "YTD May 2025", "YTD through May 2025"
    - "January through May 2025" (not full year)
    - "5 months ended May 31, 2025"
    """
    text_lower = text.lower().strip()
    year = _extract_year(text)
    
    if not year:
        return None
    
    # Don't classify full years as YTD
    if _detect_full_year_period(text):
        return None
    
    # Pattern 1: Explicit YTD prefix
    if 'ytd' in text_lower:
        month = _normalize_month(text_lower)
        if month:
            return month, year
    
    # Pattern 2: "X months ended [month]"
    months_match = re.search(r'(\d+)\s*months?\s*(ended|ending)', text_lower)
    if months_match:
        num_months = int(months_match.group(1))
        if num_months < 12:  # YTD, not full year
            month = _normalize_month(text_lower)
            if month:
                return month, year
    
    # Pattern 3: "January through [month]" where month != December
    # Also handles: "Jan - May", "Jan to May", "January thru May"
    jan_through_match = re.search(
        r'(january|jan)\s*(?:[-–—]|to|through|thru)\s*(\w+)', 
        text_lower
    )
    if jan_through_match:
        end_month_text = jan_through_match.group(2)
        end_month = _normalize_month(end_month_text)
        if end_month and end_month != 'Dec':
            return end_month, year
    
    return None


def _detect_single_month_period(text: str) -> Optional[Tuple[str, int]]:
    """
    Detect if a period label represents a single month.
    
    Returns (month_abbrev, year) or None.
    
    Patterns detected:
    - "January 2025", "Jan 2025"
    - "Month ended January 31, 2025"
    - "For the month of January 2025"
    """
    text_lower = text.lower().strip()
    year = _extract_year(text)
    
    if not year:
        return None
    
    # Don't match if it's a range or multi-month period
    if any(x in text_lower for x in ['through', 'thru', ' to ', '-', '–', '—', 'months']):
        if 'ytd' not in text_lower:  # Allow YTD detection to handle these
            return None
    
    # Pattern: Simple "Month Year" format
    for month_name, abbrev in MONTH_MAP.items():
        if month_name in text_lower:
            return abbrev, year
    
    return None


def standardize_period_label(label: str) -> str:
    """
    Convert a period label to standardized format.
    
    Standard formats:
    - Full fiscal years: FY23 (two-digit year)
    - Quarters: Q123 (Q + quarter number + two-digit year)
    - YTD periods: YTD-May-2025 (full year for YTD to avoid ambiguity)
    - Single months: Jan-2025 (month-year)
    
    Args:
        label: Raw period label from document
        
    Returns:
        Standardized period label
    """
    if not label:
        return label
    
    label_stripped = label.strip()
    
    # Check for quarter first (most specific)
    quarter_info = _detect_quarter_period(label_stripped)
    if quarter_info:
        quarter_num, year = quarter_info
        year_short = str(year)[-2:]
        return f"Q{quarter_num}{year_short}"
    
    # Check for YTD period BEFORE full year (more specific)
    # YTD period is a partial year, so check this before full year
    ytd_info = _detect_ytd_period(label_stripped)
    if ytd_info:
        month, year = ytd_info
        return f"YTD-{month}-{year}"
    
    # Check for full fiscal year
    if _detect_full_year_period(label_stripped):
        year = _extract_year(label_stripped)
        if year:
            year_short = str(year)[-2:]
            return f"FY{year_short}"
    
    # Check for single month period
    month_info = _detect_single_month_period(label_stripped)
    if month_info:
        month, year = month_info
        return f"{month}-{year}"
    
    # Fallback: try to at least extract year
    year = _extract_year(label_stripped)
    if year:
        # If we couldn't identify the period type but have a year,
        # assume it's a fiscal year
        year_short = str(year)[-2:]
        return f"FY{year_short}"
    
    # Return original if we can't standardize
    return label_stripped


def normalize_for_matching(label: str) -> str:
    """
    Normalize a period label for fuzzy matching purposes.
    
    This is more aggressive than standardize_period_label and extracts
    the core temporal components for comparison.
    
    Returns a normalized string that can be used for equality comparison.
    """
    if not label:
        return ""
    
    label_lower = label.lower().strip()
    
    # Remove common prefixes/suffixes
    label_lower = re.sub(r'^(fy|fiscal\s*year)\s*', '', label_lower)
    label_lower = re.sub(r'(year\s*ended?|as\s*of)\s*', '', label_lower)
    
    # Normalize spaces and hyphens
    label_lower = re.sub(r'\s*[-–—]\s*', '-', label_lower)
    label_lower = re.sub(r'\s+to\s+', '-', label_lower)
    label_lower = re.sub(r'\s+through\s+', '-', label_lower)
    label_lower = re.sub(r'\s+', ' ', label_lower)
    
    # Normalize month names
    for full_name, abbrev in MONTH_MAP.items():
        label_lower = label_lower.replace(full_name, abbrev.lower())
    
    # Extract year (4 digits)
    year_match = re.search(r'(19|20)(\d{2})', label_lower)
    year_full = year_match.group() if year_match else ""
    year_short = year_match.group(2) if year_match else ""
    
    # Check for quarters
    quarter_match = re.search(r'q\s*([1-4])', label_lower)
    if quarter_match:
        return f"q{quarter_match.group(1)}{year_short}"
    
    # Check for full year patterns
    if _detect_full_year_period(label):
        return year_full if year_full else year_short
    
    # Check for YTD patterns
    ytd_info = _detect_ytd_period(label)
    if ytd_info:
        month, year = ytd_info
        return f"ytd-{month.lower()}-{year}"
    
    # Check for single month
    month_info = _detect_single_month_period(label)
    if month_info:
        month, year = month_info
        return f"{month.lower()}-{year}"
    
    # Just return year if found
    if year_full:
        return year_full
    
    # Clean up and return
    return label_lower.strip()


def periods_match(label1: str, label2: str) -> bool:
    """
    Check if two period labels refer to the same period.
    
    Uses normalize_for_matching for fuzzy comparison.
    
    Args:
        label1: First period label
        label2: Second period label
        
    Returns:
        True if the periods match
    """
    if not label1 or not label2:
        return False
    
    # Direct match
    if label1.strip().lower() == label2.strip().lower():
        return True
    
    # Standardize both labels and compare
    std1 = standardize_period_label(label1)
    std2 = standardize_period_label(label2)
    
    if std1 == std2:
        return True
    
    # Normalized match (looser comparison)
    norm1 = normalize_for_matching(label1)
    norm2 = normalize_for_matching(label2)
    
    if norm1 == norm2:
        return True
    
    # Handle year-only matching (e.g., "2023" matches "FY2023", "FY23" matches "2023")
    year1 = _extract_year(label1)
    year2 = _extract_year(label2)
    
    if year1 and year2 and year1 == year2:
        # Both have same year - check if both are full year periods
        is_full1 = _detect_full_year_period(label1) or re.match(r'^(?:fy\s?)?\d{2,4}$', label1.strip().lower())
        is_full2 = _detect_full_year_period(label2) or re.match(r'^(?:fy\s?)?\d{2,4}$', label2.strip().lower())
        
        if is_full1 and is_full2:
            return True
        
        # Check if both are quarters with same quarter number
        q1 = _detect_quarter_period(label1)
        q2 = _detect_quarter_period(label2)
        
        if q1 and q2:
            if q1[0] == q2[0] and q1[1] == q2[1]:  # Same quarter, same year
                return True
    
    return False


def get_period_type(label: str) -> str:
    """
    Determine the type of period represented by a label.
    
    Returns: 'fiscal_year', 'quarter', 'ytd', 'month', or 'unknown'
    """
    if not label:
        return 'unknown'
    
    if _detect_quarter_period(label):
        return 'quarter'
    
    if _detect_full_year_period(label):
        return 'fiscal_year'
    
    if _detect_ytd_period(label):
        return 'ytd'
    
    if _detect_single_month_period(label):
        return 'month'
    
    return 'unknown'


# Test cases for validation
if __name__ == "__main__":
    test_cases = [
        # Full years
        ("2024", "FY24"),
        ("2023", "FY23"),
        ("FY2024", "FY24"),
        ("FY 2024", "FY24"),
        ("FY24", "FY24"),
        ("Year Ended December 31, 2024", "FY24"),
        ("January through December 2024", "FY24"),
        ("Jan - Dec 2024", "FY24"),
        ("Jan-Dec 2024", "FY24"),
        ("12 months ended December 31, 2024", "FY24"),
        
        # Quarters
        ("Q1 2024", "Q124"),
        ("Q3 2023", "Q323"),
        ("Q4 '24", "Q424"),
        ("First Quarter 2024", "Q124"),
        ("Three months ended March 31, 2024", "Q124"),
        ("Three months ended June 30, 2024", "Q224"),
        
        # YTD
        ("YTD May 2025", "YTD-May-2025"),
        ("January through May 2025", "YTD-May-2025"),
        ("5 months ended May 31, 2025", "YTD-May-2025"),
        
        # Single months
        ("January 2025", "Jan-2025"),
        ("Jan 2025", "Jan-2025"),
    ]
    
    print("Period Standardization Tests:")
    print("=" * 60)
    passed = 0
    failed = 0
    for input_label, expected in test_cases:
        result = standardize_period_label(input_label)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] '{input_label}' -> '{result}' (expected: '{expected}')")
    
    print(f"\nStandardization: {passed}/{len(test_cases)} passed")
    
    print("\n\nPeriod Matching Tests:")
    print("=" * 60)
    match_tests = [
        ("2023", "FY2023", True),
        ("2024", "January through December 2024", True),
        ("FY23", "2023", True),
        ("Q1 2024", "First Quarter 2024", True),
        ("2024", "2023", False),
        ("Q1 2024", "Q2 2024", False),
    ]
    passed = 0
    failed = 0
    for label1, label2, expected in match_tests:
        result = periods_match(label1, label2)
        status = "PASS" if result == expected else "FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] '{label1}' matches '{label2}'? {result} (expected: {expected})")
    
    print(f"\nMatching: {passed}/{len(match_tests)} passed")
