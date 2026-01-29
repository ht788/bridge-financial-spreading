import React from 'react';
import { Building2, Cpu, FileText, Settings2, ChevronDown, Zap, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import { 
  TestCompany, 
  AvailableModel,
  CompanyFileStatus,
} from '../../testingTypes';

interface TestConfigPanelProps {
  companies: TestCompany[];
  models: AvailableModel[];
  selectedCompany?: TestCompany;
  selectedModel?: AvailableModel;
  promptContent?: string;
  extendedThinking: boolean;
  parallel: boolean;
  maxConcurrent: number;
  companiesFileStatus?: CompanyFileStatus[];
  onSelectCompany: (company: TestCompany) => void;
  onSelectModel: (model: AvailableModel) => void;
  onPromptChange: (content: string) => void;
  onExtendedThinkingChange: (enabled: boolean) => void;
  onParallelChange: (enabled: boolean) => void;
  onMaxConcurrentChange: (value: number) => void;
  onRunTest: () => void;
  isRunning: boolean;
}

export const TestConfigPanel: React.FC<TestConfigPanelProps> = ({
  companies,
  models,
  selectedCompany,
  selectedModel,
  promptContent,
  extendedThinking,
  parallel,
  maxConcurrent,
  companiesFileStatus,
  onSelectCompany,
  onSelectModel,
  onPromptChange,
  onExtendedThinkingChange,
  onParallelChange,
  onMaxConcurrentChange,
  onRunTest,
  isRunning
}) => {
  const [showPromptEditor, setShowPromptEditor] = React.useState(false);

  // Get file status for a company
  const getCompanyFileStatus = (companyId: string): CompanyFileStatus | undefined => {
    return companiesFileStatus?.find(s => s.id === companyId);
  };

  // Check if selected company can be tested
  const selectedCompanyStatus = selectedCompany ? getCompanyFileStatus(selectedCompany.id) : undefined;
  const canTestSelectedCompany = selectedCompanyStatus?.can_test ?? true;

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 bg-gradient-to-r from-violet-500 to-purple-600 text-white">
        <h3 className="font-semibold text-lg flex items-center gap-2">
          <Settings2 className="w-5 h-5" />
          Test Configuration
        </h3>
        <p className="text-violet-100 text-sm mt-1">
          Select a company, model, and optionally customize the prompt
        </p>
      </div>

      <div className="p-6 space-y-6">
        {/* Company Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-gray-500" />
            Company to Test
          </label>
          <div className="grid grid-cols-1 gap-3">
            {companies.map((company) => {
              const fileStatus = getCompanyFileStatus(company.id);
              const hasAllFiles = !fileStatus || fileStatus.missing_files === 0;
              const hasSomeFiles = fileStatus?.can_test ?? true;
              
              return (
                <button
                  key={company.id}
                  onClick={() => onSelectCompany(company)}
                  className={`text-left p-4 rounded-xl border-2 transition-all ${
                    selectedCompany?.id === company.id
                      ? 'border-violet-500 bg-violet-50 ring-2 ring-violet-500/20'
                      : !hasSomeFiles
                        ? 'border-red-200 bg-red-50/50 opacity-75'
                        : !hasAllFiles
                          ? 'border-amber-200 bg-amber-50/30 hover:border-amber-300'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-gray-900">{company.name}</div>
                    {fileStatus && (
                      <div className="flex items-center gap-1">
                        {hasAllFiles ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : hasSomeFiles ? (
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500" />
                        )}
                      </div>
                    )}
                  </div>
                  <div className="text-sm text-gray-500 mt-1">
                    {fileStatus ? (
                      <>
                        {fileStatus.available_files}/{fileStatus.total_files} files available
                        {fileStatus.missing_files > 0 && (
                          <span className="text-amber-600 ml-1">
                            ({fileStatus.missing_files} missing)
                          </span>
                        )}
                      </>
                    ) : (
                      <>
                        {company.files.length} test file{company.files.length !== 1 ? 's' : ''}
                      </>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {company.files.map((file, idx) => (
                      <span 
                        key={idx}
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          file.doc_type === 'auto'
                            ? 'bg-purple-100 text-purple-700'
                            : file.doc_type === 'income' 
                              ? 'bg-blue-100 text-blue-700' 
                              : 'bg-emerald-100 text-emerald-700'
                        }`}
                      >
                        {file.doc_type === 'auto' ? 'Auto' : file.doc_type === 'income' ? 'P&L' : 'BS'}
                      </span>
                    ))}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Missing Files Warning */}
        {selectedCompanyStatus && selectedCompanyStatus.missing_files > 0 && (
          <div className={`p-4 rounded-xl border ${
            selectedCompanyStatus.can_test 
              ? 'bg-amber-50 border-amber-200' 
              : 'bg-red-50 border-red-200'
          }`}>
            <div className="flex items-start gap-3">
              <AlertTriangle className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                selectedCompanyStatus.can_test ? 'text-amber-600' : 'text-red-600'
              }`} />
              <div>
                <p className={`font-medium ${
                  selectedCompanyStatus.can_test ? 'text-amber-800' : 'text-red-800'
                }`}>
                  {selectedCompanyStatus.can_test 
                    ? 'Some test files are missing' 
                    : 'No test files available'}
                </p>
                <p className={`text-sm mt-1 ${
                  selectedCompanyStatus.can_test ? 'text-amber-700' : 'text-red-700'
                }`}>
                  {selectedCompanyStatus.missing_files} of {selectedCompanyStatus.total_files} files 
                  not found on the server. 
                  {selectedCompanyStatus.can_test 
                    ? ' Test will run with available files only.' 
                    : ' Please add test files to run this test.'}
                </p>
                <details className="mt-2">
                  <summary className={`text-xs cursor-pointer ${
                    selectedCompanyStatus.can_test ? 'text-amber-600' : 'text-red-600'
                  } hover:underline`}>
                    Show missing files
                  </summary>
                  <ul className="text-xs mt-1 space-y-0.5 text-gray-600">
                    {selectedCompanyStatus.files
                      .filter(f => !f.exists)
                      .map((file, idx) => (
                        <li key={idx} className="truncate">- {file.filename}</li>
                      ))}
                  </ul>
                </details>
              </div>
            </div>
          </div>
        )}

        {/* Model Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
            <Cpu className="w-4 h-4 text-gray-500" />
            Model
          </label>
          <div className="relative">
            <select
              value={selectedModel?.id || ''}
              onChange={(e) => {
                const model = models.find(m => m.id === e.target.value);
                if (model) onSelectModel(model);
              }}
              className="w-full appearance-none bg-white border border-gray-200 rounded-xl px-4 py-3 pr-10 text-gray-900 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-500 transition-all"
            >
              <option value="">Select a model...</option>
              {models.map((model) => (
                <option key={model.id} value={model.id}>
                  {model.name} {model.description ? `- ${model.description}` : ''}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Extended Thinking Toggle (for Claude models) */}
        {selectedModel && selectedModel.id.includes('claude') && (
          <div className="bg-purple-50 border border-purple-200 rounded-xl p-4">
            <label className="flex items-center justify-between cursor-pointer">
              <div className="flex items-center gap-3">
                <div className="flex-shrink-0">
                  <div className={`w-12 h-6 rounded-full transition-colors ${
                    extendedThinking ? 'bg-purple-600' : 'bg-gray-300'
                  }`}>
                    <div className={`w-5 h-5 bg-white rounded-full shadow-sm transition-transform transform ${
                      extendedThinking ? 'translate-x-6' : 'translate-x-0.5'
                    } mt-0.5`} />
                  </div>
                </div>
                <div>
                  <div className="font-medium text-gray-900">Extended Thinking</div>
                  <div className="text-sm text-gray-600">
                    Enable deeper reasoning for complex documents (uses more tokens)
                  </div>
                </div>
              </div>
              <input
                type="checkbox"
                checked={extendedThinking}
                onChange={(e) => onExtendedThinkingChange(e.target.checked)}
                className="sr-only"
              />
            </label>
          </div>
        )}

        {/* Parallel Processing Controls */}
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-4">
          <label className="flex items-center justify-between cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="flex-shrink-0">
                <div className={`w-12 h-6 rounded-full transition-colors ${
                  parallel ? 'bg-amber-600' : 'bg-gray-300'
                }`}>
                  <div className={`w-5 h-5 bg-white rounded-full shadow-sm transition-transform transform ${
                    parallel ? 'translate-x-6' : 'translate-x-0.5'
                  } mt-0.5`} />
                </div>
              </div>
              <div>
                <div className="font-medium text-gray-900 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-600" />
                  Parallel Processing
                </div>
                <div className="text-sm text-gray-600">
                  Process multiple files simultaneously for faster test execution
                </div>
              </div>
            </div>
            <input
              type="checkbox"
              checked={parallel}
              onChange={(e) => onParallelChange(e.target.checked)}
              className="sr-only"
            />
          </label>
          
          {/* Max Concurrent Slider - only shown when parallel is enabled */}
          {parallel && (
            <div className="pt-2 border-t border-amber-200">
              <div className="flex items-center justify-between mb-2">
                <label className="text-sm font-medium text-gray-700">
                  Max Concurrent Files
                </label>
                <span className="text-sm font-semibold text-amber-700 bg-amber-100 px-2 py-0.5 rounded">
                  {maxConcurrent}
                </span>
              </div>
              <input
                type="range"
                min="1"
                max="6"
                value={maxConcurrent}
                onChange={(e) => onMaxConcurrentChange(parseInt(e.target.value))}
                className="w-full h-2 bg-amber-200 rounded-lg appearance-none cursor-pointer accent-amber-600"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>1 (Safe)</span>
                <span>3 (Default)</span>
                <span>6 (Fast)</span>
              </div>
            </div>
          )}
        </div>

        {/* Prompt Editor Toggle */}
        <div>
          <button
            onClick={() => setShowPromptEditor(!showPromptEditor)}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors"
          >
            <FileText className="w-4 h-4" />
            {showPromptEditor ? 'Hide' : 'Show'} Prompt Editor
            <ChevronDown className={`w-4 h-4 transition-transform ${showPromptEditor ? 'rotate-180' : ''}`} />
          </button>
          
          {showPromptEditor && (
            <div className="mt-3">
              <textarea
                value={promptContent || ''}
                onChange={(e) => onPromptChange(e.target.value)}
                placeholder="Enter custom prompt override (leave empty to use default from LangSmith Hub)..."
                className="w-full h-48 px-4 py-3 text-sm font-mono bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-violet-500 resize-none"
              />
              <p className="text-xs text-gray-500 mt-2">
                Leave empty to use the default prompt from LangSmith Hub
              </p>
            </div>
          )}
        </div>

        {/* Run Test Button */}
        <button
          onClick={onRunTest}
          disabled={!selectedCompany || !selectedModel || isRunning || !canTestSelectedCompany}
          className={`w-full py-4 rounded-xl font-semibold text-white transition-all flex items-center justify-center gap-2 ${
            !selectedCompany || !selectedModel || isRunning || !canTestSelectedCompany
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 shadow-lg shadow-violet-500/30 hover:shadow-violet-500/40'
          }`}
        >
          {isRunning ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Running Test...
            </>
          ) : !canTestSelectedCompany ? (
            <>
              <XCircle className="w-5 h-5" />
              No Test Files Available
            </>
          ) : (
            <>
              <FileText className="w-5 h-5" />
              Run Test
            </>
          )}
        </button>
      </div>
    </div>
  );
};
