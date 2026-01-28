import React from 'react';
import { Clock, Building2, Cpu, Eye, Trash2 } from 'lucide-react';
import { 
  TestRunSummary, 
  getGradeColor, 
  formatScore, 
  formatDuration 
} from '../../testingTypes';

interface TestHistoryTableProps {
  history: TestRunSummary[];
  onViewResult: (testId: string) => void;
  isLoading?: boolean;
}

export const TestHistoryTable: React.FC<TestHistoryTableProps> = ({
  history,
  onViewResult,
  isLoading
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-8">
        <div className="flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-violet-500/30 border-t-violet-500 rounded-full animate-spin" />
          <span className="ml-3 text-gray-600">Loading history...</span>
        </div>
      </div>
    );
  }

  if (history.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-8 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Clock className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900">No Test History</h3>
        <p className="text-gray-500 mt-1">
          Run your first test to start building your history
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-200 bg-gradient-to-r from-slate-600 to-gray-700">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Test History
        </h3>
        <p className="text-gray-300 text-sm mt-1">
          {history.length} previous test run{history.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Date/Time
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Company
              </th>
              <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Model
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Grade
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Score
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Files
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Duration
              </th>
              <th className="px-4 py-3 text-center text-xs font-semibold text-gray-600 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {history.map((run) => (
              <tr key={run.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                  {new Date(run.timestamp).toLocaleDateString('en-US', { timeZone: 'America/New_York' })}{' '}
                  <span className="text-gray-400">
                    {new Date(run.timestamp).toLocaleTimeString('en-US', { 
                      timeZone: 'America/New_York',
                      hour: '2-digit', 
                      minute: '2-digit' 
                    })}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-gray-400" />
                    <span className="text-sm font-medium text-gray-900">{run.company_name}</span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-gray-400" />
                    <span className="text-sm text-gray-700">{run.model_name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-flex px-3 py-1 text-sm font-bold rounded-lg border ${getGradeColor(run.overall_grade)}`}>
                    {run.overall_grade}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="text-sm font-semibold text-gray-900">
                    {formatScore(run.overall_score)}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="text-sm text-gray-600">{run.total_files}</span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className="text-sm text-gray-600">{formatDuration(run.execution_time_seconds)}</span>
                </td>
                <td className="px-4 py-3 text-center">
                  <button
                    onClick={() => onViewResult(run.id)}
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-violet-600 hover:text-violet-700 hover:bg-violet-50 rounded-lg transition-colors"
                  >
                    <Eye className="w-4 h-4" />
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
