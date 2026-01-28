import React from 'react';
import { FileSpreadsheet, Zap, FlaskConical } from 'lucide-react';

interface HeaderProps {
  onNavigateToTesting?: () => void;
  onNavigateToHome?: () => void;
  currentPage?: 'home' | 'testing';
}

export const Header: React.FC<HeaderProps> = ({ 
  onNavigateToTesting, 
  onNavigateToHome,
  currentPage = 'home' 
}) => {
  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button 
              onClick={onNavigateToHome}
              className="flex items-center gap-3 hover:opacity-80 transition-opacity"
            >
              <div className="bg-gradient-to-br from-emerald-500 to-teal-600 p-2.5 rounded-xl shadow-lg shadow-emerald-500/20">
                <FileSpreadsheet className="w-6 h-6 text-white" />
              </div>
              <div className="text-left">
                <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  Bridge Financial Spreader
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-semibold rounded-full">
                    <Zap className="w-3 h-3" />
                    AI
                  </span>
                </h1>
                <p className="text-sm text-gray-500">
                  Vision-First Financial Statement Analysis
                </p>
              </div>
            </button>
          </div>

          {/* Navigation */}
          <div className="flex items-center gap-2">
            <button
              onClick={onNavigateToTesting}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-medium transition-all ${
                currentPage === 'testing'
                  ? 'bg-violet-100 text-violet-700 ring-2 ring-violet-500/20'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              <FlaskConical className="w-4 h-4" />
              Testing Lab
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
