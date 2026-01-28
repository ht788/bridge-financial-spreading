/**
 * Utility functions
 */

import { LineItem } from './types';

/**
 * Format a number as currency
 */
export function formatCurrency(value: number | null, currency: string = 'USD', scale: string = 'units'): string {
  if (value === null) return 'N/A';
  
  let displayValue = value;
  let suffix = '';
  
  // Adjust for scale
  if (scale === 'thousands') {
    displayValue = value * 1000;
    suffix = 'K';
  } else if (scale === 'millions') {
    displayValue = value * 1000000;
    suffix = 'M';
  } else if (scale === 'billions') {
    displayValue = value * 1000000000;
    suffix = 'B';
  }
  
  const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
  
  return formatter.format(displayValue) + (suffix ? ` ${suffix}` : '');
}

/**
 * Get confidence level label
 */
export function getConfidenceLevel(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= 0.8) return 'high';
  if (confidence >= 0.5) return 'medium';
  return 'low';
}

/**
 * Get confidence color class
 */
export function getConfidenceColor(confidence: number): string {
  const level = getConfidenceLevel(confidence);
  switch (level) {
    case 'high':
      return 'text-confidence-high';
    case 'medium':
      return 'text-confidence-medium';
    case 'low':
      return 'text-confidence-low';
  }
}

/**
 * Get confidence background color class
 */
export function getConfidenceBgColor(confidence: number): string {
  const level = getConfidenceLevel(confidence);
  switch (level) {
    case 'high':
      return 'bg-green-100';
    case 'medium':
      return 'bg-yellow-100';
    case 'low':
      return 'bg-red-100';
  }
}

/**
 * Convert field name to readable label
 */
export function fieldNameToLabel(fieldName: string): string {
  return fieldName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Normalize verbose period labels to concise display format
 * Examples:
 *   "January through December 2024" → "2024"
 *   "Year Ended December 31, 2024" → "2024"
 *   "January 2025" → "Jan 2025"
 *   "For the month ended January 31, 2025" → "Jan 2025"
 */
export function normalizePeriodLabel(label: string): string {
  if (!label) return label;
  
  // Month abbreviation map
  const monthAbbr: Record<string, string> = {
    'january': 'Jan', 'february': 'Feb', 'march': 'Mar', 'april': 'Apr',
    'may': 'May', 'june': 'Jun', 'july': 'Jul', 'august': 'Aug',
    'september': 'Sep', 'october': 'Oct', 'november': 'Nov', 'december': 'Dec'
  };
  
  const normalized = label.toLowerCase().trim();
  
  // Full year patterns - simplify to just the year
  // "January through December 2024" → "2024"
  // "Jan - Dec 2024" → "2024"
  if (/jan\w*\s*(through|to|-)\s*dec\w*\s*(\d{4})/i.test(label)) {
    const match = label.match(/(\d{4})/);
    if (match) return match[1];
  }
  
  // "Year Ended December 31, 2024" → "2024"
  // "Fiscal Year Ended..." → "FY 2024"
  if (/year\s*ended/i.test(label) || /fiscal\s*year/i.test(label)) {
    const match = label.match(/(\d{4})/);
    if (match) {
      return /fiscal/i.test(label) ? `FY ${match[1]}` : match[1];
    }
  }
  
  // "For the year ended..." → "2024"
  if (/for\s*the\s*(year|twelve\s*months)/i.test(label)) {
    const match = label.match(/(\d{4})/);
    if (match) return match[1];
  }
  
  // Single month patterns - "January 2025" → "Jan 2025"
  // "For the month ended January 31, 2025" → "Jan 2025"
  const singleMonthMatch = label.match(/\b(january|february|march|april|may|june|july|august|september|october|november|december)\b[^0-9]*(\d{4})/i);
  if (singleMonthMatch && !/through|to|-/i.test(label.replace(singleMonthMatch[0], ''))) {
    const month = monthAbbr[singleMonthMatch[1].toLowerCase()];
    const year = singleMonthMatch[2];
    return `${month} ${year}`;
  }
  
  // Quarter patterns - "Three months ended March 31, 2024" → "Q1 2024"
  if (/three\s*months\s*ended/i.test(label)) {
    const match = label.match(/(\w+)\s*\d+,?\s*(\d{4})/);
    if (match) {
      const endMonth = match[1].toLowerCase();
      const year = match[2];
      // Determine quarter based on end month
      const quarters: Record<string, string> = {
        'march': 'Q1', 'april': 'Q1',
        'june': 'Q2', 'july': 'Q2',
        'september': 'Q3', 'october': 'Q3',
        'december': 'Q4', 'january': 'Q4'
      };
      const quarter = quarters[endMonth] || '';
      if (quarter) return `${quarter} ${year}`;
    }
  }
  
  // "As of December 31, 2024" → "Dec 31, 2024" (for balance sheets)
  if (/as\s*of/i.test(label)) {
    const match = label.match(/(\w+)\s*(\d+),?\s*(\d{4})/);
    if (match) {
      const month = monthAbbr[match[1].toLowerCase()] || match[1].slice(0, 3);
      return `${month} ${match[2]}, ${match[3]}`;
    }
  }
  
  // If no pattern matches, return original but try to shorten months
  let result = label;
  Object.entries(monthAbbr).forEach(([full, abbr]) => {
    result = result.replace(new RegExp(full, 'gi'), abbr);
  });
  
  return result;
}

/**
 * Export data to JSON
 */
export function exportToJSON(data: any, filename: string): void {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

/**
 * Export data to CSV
 * Handles both single-period and multi-period data structures
 */
export function exportToCSV(data: any, filename: string, metadata?: any): void {
  // Check if this is multi-period data
  const isMultiPeriod = 'periods' in data && Array.isArray(data.periods);
  
  if (isMultiPeriod) {
    // Multi-period export: create columns for each period
    const periods = data.periods;
    const periodLabels = periods.map((p: any) => normalizePeriodLabel(p.period_label));
    
    // Build header row: Field, Period1 Value, Period1 Confidence, Period2 Value, Period2 Confidence, ...
    const headerParts = ['Field'];
    periodLabels.forEach((label: string) => {
      headerParts.push(`${label} Value`, `${label} Confidence`, `${label} Raw Fields`, `${label} Section`);
    });
    const rows: string[] = [headerParts.join(',')];
    
    // Collect all unique field names across all periods
    const allFields = new Set<string>();
    periods.forEach((period: any) => {
      Object.keys(period.data).forEach(key => {
        const item = period.data[key];
        if (typeof item === 'object' && item !== null && 'value' in item) {
          allFields.add(key);
        }
      });
    });
    
    // Build rows for each field
    allFields.forEach(fieldName => {
      const rowParts: string[] = [fieldNameToLabel(fieldName)];
      
      // Add data for each period
      periods.forEach((period: any) => {
        const lineItem = period.data[fieldName] as LineItem | undefined;
        if (lineItem && typeof lineItem === 'object' && 'value' in lineItem) {
          rowParts.push(
            lineItem.value?.toString() || '',
            lineItem.confidence.toString(),
            `"${lineItem.raw_fields_used.join('; ')}"`,
            lineItem.source_section_hint || ''
          );
        } else {
          // Field doesn't exist in this period
          rowParts.push('', '', '', '');
        }
      });
      
      rows.push(rowParts.join(','));
    });
    
    const csv = rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  } else {
    // Single-period export (original logic)
    const rows: string[] = [
      'Field,Value,Confidence,Raw Fields Used,Source Section',
    ];
    
    Object.entries(data).forEach(([fieldName, lineItem]) => {
      if (typeof lineItem === 'object' && lineItem !== null && 'value' in lineItem) {
        const item = lineItem as LineItem;
        rows.push([
          fieldNameToLabel(fieldName),
          item.value?.toString() || '',
          item.confidence.toString(),
          `"${item.raw_fields_used.join('; ')}"`,
          item.source_section_hint || '',
        ].join(','));
      }
    });
    
    const csv = rows.join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }
}
