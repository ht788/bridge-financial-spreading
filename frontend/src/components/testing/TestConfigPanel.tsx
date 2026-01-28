import React from 'react';
import { Building2, Cpu, FileText, Settings2, ChevronDown } from 'lucide-react';
import { 
  TestCompany, 
  AvailableModel,
} from '../../testingTypes';

interface TestConfigPanelProps {
  companies: TestCompany[];
  models: AvailableModel[];
  selectedCompany?: TestCompany;
  selectedModel?: AvailableModel;
  promptContent?: string;
  extendedThinking: boolean;
  onSelectCompany: (company: TestCompany) => void;
  onSelectModel: (model: AvailableModel) => void;
  onPromptChange: (content: string) => void;
  onExtendedThinkingChange: (enabled: boolean) => void;
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
  onSelectCompany,
  onSelectModel,
  onPromptChange,
  onExtendedThinkingChange,
  onRunTest,
  isRunning
}) => {
  const [showPromptEditor, setShowPromptEditor] = React.useState(false);

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
            {companies.map((company) => (
              <button
                key={company.id}
                onClick={() => onSelectCompany(company)}
                className={`text-left p-4 rounded-xl border-2 transition-all ${
                  selectedCompany?.id === company.id
                    ? 'border-violet-500 bg-violet-50 ring-2 ring-violet-500/20'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className="font-semibold text-gray-900">{company.name}</div>
                <div className="text-sm text-gray-500 mt-1">
                  {company.files.length} test file{company.files.length !== 1 ? 's' : ''}
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
            ))}
          </div>
        </div>

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
          disabled={!selectedCompany || !selectedModel || isRunning}
          className={`w-full py-4 rounded-xl font-semibold text-white transition-all flex items-center justify-center gap-2 ${
            !selectedCompany || !selectedModel || isRunning
              ? 'bg-gray-300 cursor-not-allowed'
              : 'bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 shadow-lg shadow-violet-500/30 hover:shadow-violet-500/40'
          }`}
        >
          {isRunning ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              Running Test...
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
