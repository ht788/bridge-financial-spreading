import React, { useState } from 'react';
import { 
  LineItem, 
  FinancialStatement, 
  IncomeStatement, 
  BalanceSheet,
  MultiPeriodFinancialStatement,
  MultiPeriodIncomeStatement,
  MultiPeriodBalanceSheet,
  isMultiPeriod,
} from '../types';
import { formatCurrency, fieldNameToLabel } from '../utils';
import { ConfidenceBadge } from './ConfidenceBadge';
import { Info, Calendar } from 'lucide-react';
import clsx from 'clsx';

interface FinancialTableProps {
  data: FinancialStatement | MultiPeriodFinancialStatement;
  docType: 'income' | 'balance';
}

interface TooltipProps {
  lineItem: LineItem;
  fieldName: string;
}

const Tooltip: React.FC<TooltipProps> = ({ lineItem, fieldName }) => {
  const [show, setShow] = useState(false);

  return (
    <div className="relative inline-block">
      <button
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        className="p-1 hover:bg-gray-100 rounded"
      >
        <Info className="w-3 h-3 text-gray-400" />
      </button>
      {show && (
        <div className="absolute z-10 w-72 p-3 bg-gray-900 text-white text-xs rounded-lg shadow-lg right-0 top-8">
          <div className="space-y-2">
            <div>
              <span className="font-semibold">Field:</span> {fieldNameToLabel(fieldName)}
            </div>
            <div>
              <span className="font-semibold">Confidence:</span> {Math.round(lineItem.confidence * 100)}%
            </div>
            {lineItem.raw_fields_used.length > 0 && (
              <div>
                <span className="font-semibold">Source Text:</span>
                <ul className="mt-1 space-y-1">
                  {lineItem.raw_fields_used.map((text, idx) => (
                    <li key={idx} className="pl-2 border-l-2 border-gray-600">
                      {text}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {lineItem.source_section_hint && (
              <div>
                <span className="font-semibold">Section:</span> {lineItem.source_section_hint}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// =============================================================================
// MULTI-PERIOD INCOME STATEMENT TABLE
// =============================================================================

interface MultiPeriodIncomeTableProps {
  data: MultiPeriodIncomeStatement;
}

const MultiPeriodIncomeStatementTable: React.FC<MultiPeriodIncomeTableProps> = ({ data }) => {
  const { periods, currency = 'USD', scale = 'units' } = data;
  
  const sections = [
    {
      title: 'Revenue & Gross Profit',
      fields: ['revenue', 'cogs', 'gross_profit'],
    },
    {
      title: 'Operating Expenses',
      fields: [
        'sga',
        'research_and_development',
        'depreciation_amortization',
        'other_operating_expenses',
        'total_operating_expenses',
      ],
    },
    {
      title: 'Operating Income',
      fields: ['operating_income'],
    },
    {
      title: 'Non-Operating Items',
      fields: ['interest_expense', 'interest_income', 'other_income_expense'],
    },
    {
      title: 'Net Income',
      fields: ['pretax_income', 'income_tax_expense', 'net_income'],
    },
  ];

  return (
    <div className="space-y-6">
      {sections.map((section) => (
        <div key={section.title}>
          <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
            {section.title}
          </h3>
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-gray-300">
                <th className="py-2 px-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider w-1/4">
                  Line Item
                </th>
                {periods.map((period, idx) => (
                  <th key={idx} className="py-2 px-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    <div className="flex flex-col items-end gap-0.5">
                      <span>{period.period_label}</span>
                      {period.end_date && (
                        <span className="text-[10px] text-gray-400 font-normal flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {period.end_date}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {section.fields.map((fieldName) => {
                // Check if at least one period has this field
                const hasField = periods.some(p => {
                  const lineItem = p.data[fieldName as keyof IncomeStatement] as LineItem;
                  return lineItem && typeof lineItem === 'object' && 'value' in lineItem;
                });
                
                if (!hasField) return null;

                return (
                  <tr
                    key={fieldName}
                    className={clsx(
                      'hover:bg-gray-50',
                      fieldName.includes('total') || fieldName.includes('net_income')
                        ? 'font-semibold bg-gray-50/50'
                        : ''
                    )}
                  >
                    <td className="py-2.5 px-3 text-sm text-gray-900">
                      {fieldNameToLabel(fieldName)}
                    </td>
                    {periods.map((period, periodIdx) => {
                      const lineItem = period.data[fieldName as keyof IncomeStatement] as LineItem;
                      if (!lineItem || typeof lineItem !== 'object' || !('value' in lineItem)) {
                        return <td key={periodIdx} className="py-2.5 px-3 text-sm text-right font-mono text-gray-400">—</td>;
                      }
                      
                      return (
                        <td key={periodIdx} className="py-2.5 px-3 text-sm text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <span className="font-mono">
                              {formatCurrency(lineItem.value, currency, scale)}
                            </span>
                            <ConfidenceBadge confidence={lineItem.confidence} compact />
                            <Tooltip lineItem={lineItem} fieldName={fieldName} />
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
};

// =============================================================================
// MULTI-PERIOD BALANCE SHEET TABLE
// =============================================================================

interface MultiPeriodBalanceTableProps {
  data: MultiPeriodBalanceSheet;
}

const MultiPeriodBalanceSheetTable: React.FC<MultiPeriodBalanceTableProps> = ({ data }) => {
  const { periods, currency = 'USD', scale = 'units' } = data;
  
  const sections = [
    {
      title: 'Current Assets',
      fields: [
        'cash_and_equivalents',
        'short_term_investments',
        'accounts_receivable',
        'inventory',
        'prepaid_expenses',
        'other_current_assets',
        'total_current_assets',
      ],
    },
    {
      title: 'Non-Current Assets',
      fields: [
        'ppe_gross',
        'accumulated_depreciation',
        'ppe_net',
        'intangible_assets',
        'goodwill',
        'long_term_investments',
        'other_non_current_assets',
        'total_non_current_assets',
      ],
    },
    {
      title: 'Total Assets',
      fields: ['total_assets'],
    },
    {
      title: 'Current Liabilities',
      fields: [
        'accounts_payable',
        'short_term_debt',
        'accrued_expenses',
        'deferred_revenue_current',
        'other_current_liabilities',
        'total_current_liabilities',
      ],
    },
    {
      title: 'Non-Current Liabilities',
      fields: [
        'long_term_debt',
        'deferred_tax_liabilities',
        'pension_liabilities',
        'other_non_current_liabilities',
        'total_non_current_liabilities',
      ],
    },
    {
      title: 'Total Liabilities',
      fields: ['total_liabilities'],
    },
    {
      title: "Shareholders' Equity",
      fields: [
        'common_stock',
        'additional_paid_in_capital',
        'retained_earnings',
        'treasury_stock',
        'accumulated_other_comprehensive_income',
        'total_shareholders_equity',
      ],
    },
    {
      title: 'Total Liabilities & Equity',
      fields: ['total_liabilities_and_equity'],
    },
  ];

  return (
    <div className="space-y-6">
      {sections.map((section) => (
        <div key={section.title}>
          <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
            {section.title}
          </h3>
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-gray-300">
                <th className="py-2 px-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider w-1/4">
                  Line Item
                </th>
                {periods.map((period, idx) => (
                  <th key={idx} className="py-2 px-3 text-right text-xs font-semibold text-gray-600 uppercase tracking-wider">
                    <div className="flex flex-col items-end gap-0.5">
                      <span>{period.period_label}</span>
                      {period.end_date && (
                        <span className="text-[10px] text-gray-400 font-normal flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          {period.end_date}
                        </span>
                      )}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {section.fields.map((fieldName) => {
                // Check if at least one period has this field
                const hasField = periods.some(p => {
                  const lineItem = p.data[fieldName as keyof BalanceSheet] as LineItem;
                  return lineItem && typeof lineItem === 'object' && 'value' in lineItem;
                });
                
                if (!hasField) return null;

                return (
                  <tr
                    key={fieldName}
                    className={clsx(
                      'hover:bg-gray-50',
                      fieldName.includes('total') ? 'font-semibold bg-gray-50/50' : ''
                    )}
                  >
                    <td className="py-2.5 px-3 text-sm text-gray-900">
                      {fieldNameToLabel(fieldName)}
                    </td>
                    {periods.map((period, periodIdx) => {
                      const lineItem = period.data[fieldName as keyof BalanceSheet] as LineItem;
                      if (!lineItem || typeof lineItem !== 'object' || !('value' in lineItem)) {
                        return <td key={periodIdx} className="py-2.5 px-3 text-sm text-right font-mono text-gray-400">—</td>;
                      }
                      
                      return (
                        <td key={periodIdx} className="py-2.5 px-3 text-sm text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <span className="font-mono">
                              {formatCurrency(lineItem.value, currency, scale)}
                            </span>
                            <ConfidenceBadge confidence={lineItem.confidence} compact />
                            <Tooltip lineItem={lineItem} fieldName={fieldName} />
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
};

// =============================================================================
// SINGLE-PERIOD TABLES (Legacy support)
// =============================================================================

const SinglePeriodIncomeStatementTable: React.FC<{ data: IncomeStatement }> = ({ data }) => {
  const sections = [
    {
      title: 'Revenue & Gross Profit',
      fields: ['revenue', 'cogs', 'gross_profit'],
    },
    {
      title: 'Operating Expenses',
      fields: [
        'sga',
        'research_and_development',
        'depreciation_amortization',
        'other_operating_expenses',
        'total_operating_expenses',
      ],
    },
    {
      title: 'Operating Income',
      fields: ['operating_income'],
    },
    {
      title: 'Non-Operating Items',
      fields: ['interest_expense', 'interest_income', 'other_income_expense'],
    },
    {
      title: 'Net Income',
      fields: ['pretax_income', 'income_tax_expense', 'net_income'],
    },
  ];

  return (
    <div className="space-y-6">
      {sections.map((section) => (
        <div key={section.title}>
          <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
            {section.title}
          </h3>
          <table className="w-full">
            <tbody className="divide-y divide-gray-200">
              {section.fields.map((fieldName) => {
                const lineItem = data[fieldName as keyof IncomeStatement] as LineItem;
                if (!lineItem || typeof lineItem !== 'object' || !('value' in lineItem)) return null;

                return (
                  <tr
                    key={fieldName}
                    className={clsx(
                      'hover:bg-gray-50',
                      fieldName.includes('total') || fieldName.includes('net_income')
                        ? 'font-semibold'
                        : ''
                    )}
                  >
                    <td className="py-3 px-4 text-sm text-gray-900">
                      {fieldNameToLabel(fieldName)}
                    </td>
                    <td className="py-3 px-4 text-sm text-right font-mono">
                      {formatCurrency(lineItem.value, data.currency, data.scale)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <ConfidenceBadge confidence={lineItem.confidence} />
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Tooltip lineItem={lineItem} fieldName={fieldName} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
};

const SinglePeriodBalanceSheetTable: React.FC<{ data: BalanceSheet }> = ({ data }) => {
  const sections = [
    {
      title: 'Current Assets',
      fields: [
        'cash_and_equivalents',
        'short_term_investments',
        'accounts_receivable',
        'inventory',
        'prepaid_expenses',
        'other_current_assets',
        'total_current_assets',
      ],
    },
    {
      title: 'Non-Current Assets',
      fields: [
        'ppe_gross',
        'accumulated_depreciation',
        'ppe_net',
        'intangible_assets',
        'goodwill',
        'long_term_investments',
        'other_non_current_assets',
        'total_non_current_assets',
      ],
    },
    {
      title: 'Total Assets',
      fields: ['total_assets'],
    },
    {
      title: 'Current Liabilities',
      fields: [
        'accounts_payable',
        'short_term_debt',
        'accrued_expenses',
        'deferred_revenue_current',
        'other_current_liabilities',
        'total_current_liabilities',
      ],
    },
    {
      title: 'Non-Current Liabilities',
      fields: [
        'long_term_debt',
        'deferred_tax_liabilities',
        'pension_liabilities',
        'other_non_current_liabilities',
        'total_non_current_liabilities',
      ],
    },
    {
      title: 'Total Liabilities',
      fields: ['total_liabilities'],
    },
    {
      title: "Shareholders' Equity",
      fields: [
        'common_stock',
        'additional_paid_in_capital',
        'retained_earnings',
        'treasury_stock',
        'accumulated_other_comprehensive_income',
        'total_shareholders_equity',
      ],
    },
    {
      title: 'Total Liabilities & Equity',
      fields: ['total_liabilities_and_equity'],
    },
  ];

  return (
    <div className="space-y-6">
      {sections.map((section) => (
        <div key={section.title}>
          <h3 className="text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wide">
            {section.title}
          </h3>
          <table className="w-full">
            <tbody className="divide-y divide-gray-200">
              {section.fields.map((fieldName) => {
                const lineItem = data[fieldName as keyof BalanceSheet] as LineItem;
                if (!lineItem || typeof lineItem !== 'object' || !('value' in lineItem)) return null;

                return (
                  <tr
                    key={fieldName}
                    className={clsx(
                      'hover:bg-gray-50',
                      fieldName.includes('total') ? 'font-semibold' : ''
                    )}
                  >
                    <td className="py-3 px-4 text-sm text-gray-900">
                      {fieldNameToLabel(fieldName)}
                    </td>
                    <td className="py-3 px-4 text-sm text-right font-mono">
                      {formatCurrency(lineItem.value, data.currency, data.scale)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <ConfidenceBadge confidence={lineItem.confidence} />
                    </td>
                    <td className="py-3 px-4 text-center">
                      <Tooltip lineItem={lineItem} fieldName={fieldName} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
};

// =============================================================================
// MAIN EXPORT
// =============================================================================

export const FinancialTable: React.FC<FinancialTableProps> = ({ data, docType }) => {
  // Check if we have multi-period data
  const multiPeriod = isMultiPeriod(data);
  
  // Get period info for display
  let periodDisplay = '';
  let currencyDisplay = 'USD';
  let scaleDisplay = 'units';
  let numPeriods = 1;
  
  if (multiPeriod) {
    const mpData = data as MultiPeriodFinancialStatement;
    numPeriods = mpData.periods.length;
    currencyDisplay = mpData.currency || 'USD';
    scaleDisplay = mpData.scale || 'units';
    periodDisplay = mpData.periods.map(p => p.period_label).join(', ');
  } else {
    const spData = data as FinancialStatement;
    periodDisplay = (spData as any).fiscal_period || (spData as any).as_of_date || '';
    currencyDisplay = (spData as any).currency || 'USD';
    scaleDisplay = (spData as any).scale || 'units';
  }
  
  return (
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">
            {docType === 'income' ? 'Income Statement' : 'Balance Sheet'}
          </h2>
          {numPeriods > 1 && (
            <span className="px-3 py-1 bg-emerald-100 text-emerald-700 text-sm font-medium rounded-full">
              {numPeriods} Periods
            </span>
          )}
        </div>
        <div className="mt-2 flex items-center gap-4 text-sm text-gray-600">
          {periodDisplay && <span>Period: {periodDisplay}</span>}
          {currencyDisplay && <span>Currency: {currencyDisplay}</span>}
          {scaleDisplay && <span>Scale: {scaleDisplay}</span>}
        </div>
      </div>

      <div className="mb-4 flex items-center gap-4 text-xs">
        <span className="font-medium text-gray-700">Confidence:</span>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-confidence-high" />
          <span className="text-gray-600">High (≥80%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-confidence-medium" />
          <span className="text-gray-600">Medium (50-80%)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-confidence-low" />
          <span className="text-gray-600">Low (&lt;50%)</span>
        </div>
      </div>

      {multiPeriod ? (
        docType === 'income' ? (
          <MultiPeriodIncomeStatementTable data={data as MultiPeriodIncomeStatement} />
        ) : (
          <MultiPeriodBalanceSheetTable data={data as MultiPeriodBalanceSheet} />
        )
      ) : (
        docType === 'income' ? (
          <SinglePeriodIncomeStatementTable data={data as IncomeStatement} />
        ) : (
          <SinglePeriodBalanceSheetTable data={data as BalanceSheet} />
        )
      )}
    </div>
  );
};
