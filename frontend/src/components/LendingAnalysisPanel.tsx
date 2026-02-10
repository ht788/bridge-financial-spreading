import React, { useState, useMemo } from 'react';
import { 
  MultiPeriodIncomeStatement, 
  IncomeStatement,
  LineItem,
  isMultiPeriod,
  FinancialStatement,
  MultiPeriodFinancialStatement 
} from '../types';
import { formatCurrency, normalizePeriodLabel } from '../utils';
import { 
  AlertTriangle, 
  CheckCircle, 
  TrendingDown, 
  TrendingUp,
  DollarSign,
  Percent,
  Info,
  ChevronDown,
  ChevronUp,
  Calculator
} from 'lucide-react';
import clsx from 'clsx';

interface LendingAnalysisPanelProps {
  data: FinancialStatement | MultiPeriodFinancialStatement;
  currency?: string;
  scale?: string;
}

interface PeriodAnalysis {
  periodLabel: string;
  revenue: number | null;
  cogs: number | null;
  grossProfit: number | null;
  actualMargin: number | null;
  assumedFinanceAmount: number | null; // (1 - assumedMargin) * revenue
  isChallenged: boolean;
  shortfall: number | null; // How much we'd lose if challenged
  marginBuffer: number | null; // Actual margin - assumed margin
}

const DEFAULT_MARGIN = 30; // 30% default assumed margin

export const LendingAnalysisPanel: React.FC<LendingAnalysisPanelProps> = ({ 
  data, 
  currency = 'USD', 
  scale = 'units' 
}) => {
  const [assumedMargin, setAssumedMargin] = useState(DEFAULT_MARGIN);
  const [isExpanded, setIsExpanded] = useState(true);

  // Extract income statement periods
  const periods = useMemo(() => {
    if (isMultiPeriod(data)) {
      const multiData = data as MultiPeriodIncomeStatement;
      return multiData.periods.map(p => ({
        periodLabel: p.period_label,
        data: p.data
      }));
    } else {
      const singleData = data as IncomeStatement;
      // Check if this is actually an income statement (has revenue)
      if ('revenue' in singleData) {
        return [{
          periodLabel: singleData.fiscal_period || 'Current Period',
          data: singleData
        }];
      }
      return [];
    }
  }, [data]);

  // If no income statement data, don't render
  if (periods.length === 0) {
    return null;
  }

  // Analyze each period
  const analysis: PeriodAnalysis[] = useMemo(() => {
    const marginDecimal = assumedMargin / 100;
    const financePercentage = 1 - marginDecimal; // What we'd finance (cost portion)

    return periods.map(period => {
      const incomeData = period.data as IncomeStatement;
      
      const revenue = (incomeData.revenue as LineItem)?.value;
      const cogs = (incomeData.cogs as LineItem)?.value;
      const grossProfit = (incomeData.gross_profit as LineItem)?.value;

      // Calculate actual margin
      let actualMargin: number | null = null;
      if (revenue && revenue > 0 && grossProfit !== null) {
        actualMargin = (grossProfit / revenue) * 100;
      }

      // Calculate what we would have financed (cost portion)
      const assumedFinanceAmount = revenue ? revenue * financePercentage : null;

      // A period is "challenged" if actual margin < assumed margin
      // This means the actual cost was higher than what we assumed we were financing
      const isChallenged = actualMargin !== null && actualMargin < assumedMargin;

      // Calculate shortfall: how much we'd lose
      // If actual COGS > assumed finance amount, we have a shortfall
      let shortfall: number | null = null;
      if (cogs !== null && assumedFinanceAmount !== null && isChallenged) {
        shortfall = cogs - assumedFinanceAmount;
      }

      // Margin buffer: how much cushion we have
      const marginBuffer = actualMargin !== null ? actualMargin - assumedMargin : null;

      return {
        periodLabel: period.periodLabel,
        revenue,
        cogs,
        grossProfit,
        actualMargin,
        assumedFinanceAmount,
        isChallenged,
        shortfall,
        marginBuffer
      };
    });
  }, [periods, assumedMargin]);

  // Summary statistics
  const summary = useMemo(() => {
    const totalPeriods = analysis.length;
    const challengedPeriods = analysis.filter(a => a.isChallenged).length;
    const challengedRate = totalPeriods > 0 ? (challengedPeriods / totalPeriods) * 100 : 0;
    
    const totalRevenue = analysis.reduce((sum, a) => sum + (a.revenue || 0), 0);
    const totalCogs = analysis.reduce((sum, a) => sum + (a.cogs || 0), 0);
    const totalShortfall = analysis
      .filter(a => a.isChallenged && a.shortfall !== null)
      .reduce((sum, a) => sum + (a.shortfall || 0), 0);

    const avgActualMargin = analysis
      .filter(a => a.actualMargin !== null)
      .reduce((sum, a, _, arr) => sum + (a.actualMargin || 0) / arr.length, 0);

    // Total financed amount (what we would have advanced)
    const totalFinanced = totalRevenue * (1 - assumedMargin / 100);

    return {
      totalPeriods,
      challengedPeriods,
      challengedRate,
      totalRevenue,
      totalCogs,
      totalShortfall,
      avgActualMargin,
      totalFinanced
    };
  }, [analysis, assumedMargin]);

  // Determine overall health
  const overallHealth = summary.challengedRate === 0 
    ? 'healthy' 
    : summary.challengedRate < 25 
      ? 'caution' 
      : 'risk';

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div 
        className={clsx(
          "px-4 py-3 flex items-center justify-between cursor-pointer transition-colors",
          overallHealth === 'healthy' && "bg-emerald-50 border-b border-emerald-100",
          overallHealth === 'caution' && "bg-amber-50 border-b border-amber-100",
          overallHealth === 'risk' && "bg-red-50 border-b border-red-100"
        )}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <Calculator className={clsx(
            "w-5 h-5",
            overallHealth === 'healthy' && "text-emerald-600",
            overallHealth === 'caution' && "text-amber-600",
            overallHealth === 'risk' && "text-red-600"
          )} />
          <div>
            <h3 className="font-semibold text-gray-900">PO Lending Backtest Analysis</h3>
            <p className="text-xs text-gray-500">
              Evaluate financing risk based on assumed margins
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          {/* Quick Summary Badge */}
          <div className={clsx(
            "px-3 py-1 rounded-full text-sm font-medium",
            overallHealth === 'healthy' && "bg-emerald-100 text-emerald-700",
            overallHealth === 'caution' && "bg-amber-100 text-amber-700",
            overallHealth === 'risk' && "bg-red-100 text-red-700"
          )}>
            {summary.challengedPeriods}/{summary.totalPeriods} periods challenged
          </div>
          {isExpanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>

      {isExpanded && (
        <div className="p-4 space-y-6">
          {/* Margin Slider */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <label className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <Percent className="w-4 h-4 text-gray-500" />
                Assumed Gross Margin
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  value={assumedMargin}
                  onChange={(e) => setAssumedMargin(Math.min(100, Math.max(0, Number(e.target.value))))}
                  className="w-16 px-2 py-1 text-sm border border-gray-300 rounded text-right font-mono"
                  min="0"
                  max="100"
                  step="1"
                />
                <span className="text-sm text-gray-500">%</span>
              </div>
            </div>
            <input
              type="range"
              min="0"
              max="70"
              step="5"
              value={assumedMargin}
              onChange={(e) => setAssumedMargin(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>0%</span>
              <span>35%</span>
              <span>70%</span>
            </div>
            <p className="text-xs text-gray-500 mt-2 flex items-start gap-1">
              <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
              At {assumedMargin}% margin, you would finance {100 - assumedMargin}% of each PO (the cost portion).
              E.g., $100k PO → finance ${(100 * (100 - assumedMargin) / 100).toFixed(0)}k
            </p>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total Revenue</div>
              <div className="text-lg font-semibold font-mono text-gray-900">
                {formatCurrency(summary.totalRevenue, currency, scale)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                (Total PO value)
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Would Finance</div>
              <div className="text-lg font-semibold font-mono text-blue-600">
                {formatCurrency(summary.totalFinanced, currency, scale)}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {100 - assumedMargin}% of revenue
              </div>
            </div>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Avg Actual Margin</div>
              <div className={clsx(
                "text-lg font-semibold font-mono",
                summary.avgActualMargin >= assumedMargin ? "text-emerald-600" : "text-red-600"
              )}>
                {summary.avgActualMargin.toFixed(1)}%
              </div>
              <div className="text-xs text-gray-500 mt-1">
                {summary.avgActualMargin >= assumedMargin ? (
                  <span className="text-emerald-600">+{(summary.avgActualMargin - assumedMargin).toFixed(1)}% buffer</span>
                ) : (
                  <span className="text-red-600">{(summary.avgActualMargin - assumedMargin).toFixed(1)}% shortfall</span>
                )}
              </div>
            </div>
            <div className={clsx(
              "rounded-lg p-3",
              summary.challengedPeriods === 0 ? "bg-emerald-50" : "bg-red-50"
            )}>
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Challenged</div>
              <div className={clsx(
                "text-lg font-semibold",
                summary.challengedPeriods === 0 ? "text-emerald-600" : "text-red-600"
              )}>
                {summary.challengedRate.toFixed(0)}%
              </div>
              <div className={clsx(
                "text-xs mt-1",
                summary.challengedPeriods === 0 ? "text-emerald-600" : "text-red-600"
              )}>
                {summary.challengedPeriods} of {summary.totalPeriods} periods
              </div>
            </div>
          </div>

          {/* Total Shortfall Alert */}
          {summary.totalShortfall > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-red-800">
                  Total Potential Loss: {formatCurrency(summary.totalShortfall, currency, scale)}
                </p>
                <p className="text-xs text-red-600 mt-1">
                  If all POs were financed at {assumedMargin}% assumed margin, 
                  you would have lost this amount due to actual costs exceeding financed amounts.
                </p>
              </div>
            </div>
          )}

          {/* Period-by-Period Analysis */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wide">
              Period-by-Period Analysis
            </h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-gray-200">
                    <th className="py-2 px-3 text-left text-xs font-semibold text-gray-600 uppercase">Period</th>
                    <th className="py-2 px-3 text-right text-xs font-semibold text-gray-600 uppercase">Revenue (PO Value)</th>
                    <th className="py-2 px-3 text-right text-xs font-semibold text-gray-600 uppercase">Actual COGS</th>
                    <th className="py-2 px-3 text-right text-xs font-semibold text-gray-600 uppercase">Financed Amount</th>
                    <th className="py-2 px-3 text-right text-xs font-semibold text-gray-600 uppercase">Actual Margin</th>
                    <th className="py-2 px-3 text-center text-xs font-semibold text-gray-600 uppercase">Status</th>
                    <th className="py-2 px-3 text-right text-xs font-semibold text-gray-600 uppercase">Margin Buffer</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {analysis.map((period, idx) => (
                    <tr 
                      key={idx}
                      className={clsx(
                        "hover:bg-gray-50 transition-colors",
                        period.isChallenged && "bg-red-50/50"
                      )}
                    >
                      <td className="py-2.5 px-3 font-medium text-gray-900">
                        {normalizePeriodLabel(period.periodLabel)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">
                        {period.revenue !== null 
                          ? formatCurrency(period.revenue, currency, scale)
                          : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">
                        {period.cogs !== null 
                          ? formatCurrency(period.cogs, currency, scale)
                          : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-blue-600">
                        {period.assumedFinanceAmount !== null 
                          ? formatCurrency(period.assumedFinanceAmount, currency, scale)
                          : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono">
                        {period.actualMargin !== null ? (
                          <span className={clsx(
                            period.actualMargin >= assumedMargin ? "text-emerald-600" : "text-red-600"
                          )}>
                            {period.actualMargin.toFixed(1)}%
                          </span>
                        ) : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        {period.isChallenged ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-medium">
                            <AlertTriangle className="w-3 h-3" />
                            Challenged
                          </span>
                        ) : period.actualMargin !== null ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded-full text-xs font-medium">
                            <CheckCircle className="w-3 h-3" />
                            OK
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {period.marginBuffer !== null ? (
                          <div className="flex items-center justify-end gap-1">
                            {period.marginBuffer >= 0 ? (
                              <TrendingUp className="w-3 h-3 text-emerald-500" />
                            ) : (
                              <TrendingDown className="w-3 h-3 text-red-500" />
                            )}
                            <span className={clsx(
                              "font-mono text-sm",
                              period.marginBuffer >= 0 ? "text-emerald-600" : "text-red-600"
                            )}>
                              {period.marginBuffer >= 0 ? '+' : ''}{period.marginBuffer.toFixed(1)}%
                            </span>
                          </div>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Explanation */}
          <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 text-sm text-blue-800">
            <h5 className="font-semibold mb-2 flex items-center gap-2">
              <Info className="w-4 h-4" />
              How PO Financing Backtest Works
            </h5>
            <ul className="space-y-1 text-xs text-blue-700">
              <li>• <strong>Assumed Margin:</strong> The gross margin you expect on POs (set above)</li>
              <li>• <strong>Financed Amount:</strong> The cost portion you would advance = Revenue × (1 - Assumed Margin)</li>
              <li>• <strong>Challenged:</strong> When actual COGS exceeds the financed amount (actual margin &lt; assumed margin)</li>
              <li>• <strong>Example:</strong> $100k PO at 40% assumed margin → finance $60k. If actual COGS was $65k (35% margin), you're short $5k</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};
