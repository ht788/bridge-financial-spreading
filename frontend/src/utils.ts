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
 */
export function exportToCSV(data: Record<string, LineItem>, filename: string, metadata?: any): void {
  const rows: string[] = [
    'Field,Value,Confidence,Raw Fields Used,Source Section',
  ];
  
  Object.entries(data).forEach(([fieldName, lineItem]) => {
    if (typeof lineItem === 'object' && 'value' in lineItem) {
      rows.push([
        fieldNameToLabel(fieldName),
        lineItem.value?.toString() || '',
        lineItem.confidence.toString(),
        `"${lineItem.raw_fields_used.join('; ')}"`,
        lineItem.source_section_hint || '',
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
