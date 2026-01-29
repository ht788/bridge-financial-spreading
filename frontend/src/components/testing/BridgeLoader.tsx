import React, { useEffect, useState } from 'react';
import { FileText, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';

export interface TestProgress {
  phase: 'initializing' | 'loading' | 'extracting' | 'grading' | 'file_complete' | 'file_error' | 'complete';
  message: string;
  elapsed_seconds?: number;
  total_files?: number;
  current_file?: number;
  current_filename?: string;
  files_completed?: number;
  doc_type?: string;
  file_score?: number;
  file_grade?: string;
  overall_score?: number;
  overall_grade?: string;
  sub_phase?: string;
  error?: string;
}

interface BridgeLoaderProps {
  progress?: TestProgress | null;
}

export const BridgeLoader: React.FC<BridgeLoaderProps> = ({ progress }) => {
  const [messageIndex, setMessageIndex] = useState(0);

  const defaultMessages = [
    "Analyzing financial documents...",
    "Constructing data models...",
    "Bridging the gap between PDF and Excel...",
    "Applying financial logic...",
    "Validating extraction results...",
    "Polishing the numbers...",
    "Finalizing the spread..."
  ];

  useEffect(() => {
    // Only cycle through default messages if no progress data
    if (!progress) {
      const interval = setInterval(() => {
        setMessageIndex((prev) => (prev + 1) % defaultMessages.length);
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [progress]);

  // Calculate progress percentage
  const progressPercent = progress && progress.total_files && progress.files_completed !== undefined
    ? Math.round((progress.files_completed / progress.total_files) * 100)
    : 0;

  // Get phase-specific icon and color
  const getPhaseInfo = (phase?: string) => {
    switch (phase) {
      case 'initializing':
      case 'loading':
        return { icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-500/10' };
      case 'extracting':
        return { icon: FileText, color: 'text-violet-500', bg: 'bg-violet-500/10' };
      case 'grading':
        return { icon: Loader2, color: 'text-amber-500', bg: 'bg-amber-500/10' };
      case 'file_complete':
        return { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10' };
      case 'file_error':
        return { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-500/10' };
      case 'complete':
        return { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-500/10' };
      default:
        return { icon: Loader2, color: 'text-violet-500', bg: 'bg-violet-500/10' };
    }
  };

  const phaseInfo = getPhaseInfo(progress?.phase);
  const PhaseIcon = phaseInfo.icon;

  // Format elapsed time
  const formatTime = (seconds?: number) => {
    if (!seconds) return '0s';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-white/95 backdrop-blur-md transition-all duration-500">
      <div className="relative w-full max-w-2xl aspect-[2/1] flex items-center justify-center overflow-hidden rounded-3xl bg-gradient-to-b from-slate-900 to-slate-800 shadow-2xl p-8 mb-8 ring-1 ring-white/10">
        
        {/* Background Grid */}
        <div className="absolute inset-0 opacity-20" 
             style={{ 
               backgroundImage: 'linear-gradient(#4f46e5 1px, transparent 1px), linear-gradient(90deg, #4f46e5 1px, transparent 1px)', 
               backgroundSize: '40px 40px',
               animation: 'grid-move 20s linear infinite'
             }} 
        />

        {/* Bridge Animation Container */}
        <div className="relative w-full h-full flex items-end justify-center pb-10">
          
          {/* Water Reflection */}
          <div className="absolute bottom-0 w-full h-20 bg-gradient-to-t from-blue-500/10 to-transparent blur-xl" />

          {/* Left Tower */}
          <div className="relative z-10 flex flex-col items-center mr-32 animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <div className="w-4 h-4 rounded-full bg-violet-400 shadow-[0_0_15px_rgba(167,139,250,0.8)] animate-pulse" />
            <div className="w-2 h-40 bg-gradient-to-b from-violet-500 to-slate-800 rounded-t-lg" />
            <div className="absolute bottom-0 w-12 h-4 bg-slate-700 rounded-t-lg" />
          </div>

          {/* Right Tower */}
          <div className="relative z-10 flex flex-col items-center ml-32 animate-slide-up" style={{ animationDelay: '0.4s' }}>
            <div className="w-4 h-4 rounded-full bg-violet-400 shadow-[0_0_15px_rgba(167,139,250,0.8)] animate-pulse" />
            <div className="w-2 h-40 bg-gradient-to-b from-violet-500 to-slate-800 rounded-t-lg" />
            <div className="absolute bottom-0 w-12 h-4 bg-slate-700 rounded-t-lg" />
          </div>

          {/* Main Deck */}
          <div className="absolute bottom-20 left-0 right-0 h-1 bg-slate-600 overflow-hidden">
            <div className="h-full w-full bg-gradient-to-r from-transparent via-violet-400 to-transparent animate-shimmer" />
          </div>

          {/* Suspension Cables */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none z-0" style={{ bottom: '5rem' }}>
            {/* Main Cable */}
            <path 
              d="M 200 40 Q 400 180 600 40" 
              fill="none" 
              stroke="url(#cableGradient)" 
              strokeWidth="2"
              className="animate-draw-cable"
              strokeDasharray="1000"
              strokeDashoffset="1000"
            />
            <defs>
              <linearGradient id="cableGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0" />
                <stop offset="50%" stopColor="#8b5cf6" />
                <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
              </linearGradient>
            </defs>
          </svg>

          {/* Moving Data Packets */}
          <div className="absolute bottom-[5.1rem] left-0 right-0 h-2 z-20">
             <div className="absolute top-0 left-[20%] w-3 h-3 bg-white rounded-full shadow-[0_0_10px_white] animate-travel-right" />
             <div className="absolute top-0 left-[20%] w-2 h-2 bg-blue-400 rounded-full shadow-[0_0_10px_#60a5fa] animate-travel-right" style={{ animationDelay: '1.5s' }} />
             <div className="absolute top-0 left-[20%] w-2 h-2 bg-purple-400 rounded-full shadow-[0_0_10px_#c084fc] animate-travel-right" style={{ animationDelay: '0.8s' }} />
          </div>

        </div>
      </div>

      <div className="text-center space-y-3 z-10">
        <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-violet-600 to-blue-600 animate-pulse">
          Building the Bridge
        </h2>
        <div className="h-8 overflow-hidden">
          <p key={progress?.message || messageIndex} className="text-gray-500 font-medium animate-slide-up-fade">
            {progress?.message || defaultMessages[messageIndex]}
          </p>
        </div>
      </div>

      {/* Progress Panel - Only show when we have progress data */}
      {progress && (
        <div className="mt-8 w-full max-w-2xl bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
          {/* Progress Header */}
          <div className="bg-gradient-to-r from-violet-50 to-blue-50 px-6 py-4 border-b border-gray-100">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg ${phaseInfo.bg}`}>
                  <PhaseIcon className={`w-5 h-5 ${phaseInfo.color} ${progress.phase === 'extracting' || progress.phase === 'grading' || progress.phase === 'loading' || progress.phase === 'initializing' ? 'animate-spin' : ''}`} />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900 capitalize">
                    {progress.phase === 'extracting' && progress.sub_phase === 'llm_call' 
                      ? 'Calling AI Model' 
                      : progress.phase?.replace('_', ' ') || 'Processing'}
                  </h3>
                  <p className="text-sm text-gray-500">
                    {progress.elapsed_seconds !== undefined && `Elapsed: ${formatTime(progress.elapsed_seconds)}`}
                  </p>
                </div>
              </div>
              
              {/* File Counter */}
              {progress.total_files !== undefined && progress.files_completed !== undefined && (
                <div className="text-right">
                  <div className="text-2xl font-bold text-gray-900">
                    {progress.files_completed}<span className="text-gray-400">/{progress.total_files}</span>
                  </div>
                  <p className="text-xs text-gray-500">Files Completed</p>
                </div>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          {progress.total_files && progress.total_files > 0 && (
            <div className="px-6 py-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Overall Progress</span>
                <span className="text-sm font-semibold text-violet-600">{progressPercent}%</span>
              </div>
              <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-violet-500 to-blue-500 rounded-full transition-all duration-500 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>
          )}

          {/* Current File Info */}
          {progress.current_filename && progress.phase !== 'complete' && (
            <div className="px-6 py-4 border-t border-gray-100 bg-gray-50/50">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-gray-400" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {progress.current_filename}
                  </p>
                  <p className="text-xs text-gray-500">
                    {progress.doc_type && `${progress.doc_type.charAt(0).toUpperCase() + progress.doc_type.slice(1)} Statement`}
                    {progress.current_file && progress.total_files && ` • File ${progress.current_file} of ${progress.total_files}`}
                  </p>
                </div>
                
                {/* File score if available */}
                {progress.file_score !== undefined && (
                  <div className="text-right">
                    <span className={`text-lg font-bold ${
                      progress.file_score >= 90 ? 'text-green-600' :
                      progress.file_score >= 70 ? 'text-amber-600' :
                      'text-red-600'
                    }`}>
                      {progress.file_score}%
                    </span>
                    {progress.file_grade && (
                      <p className="text-xs text-gray-500">{progress.file_grade}</p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Completion Summary */}
          {progress.phase === 'complete' && progress.overall_score !== undefined && (
            <div className="px-6 py-4 border-t border-gray-100 bg-gradient-to-r from-green-50 to-emerald-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <CheckCircle className="w-6 h-6 text-green-500" />
                  <div>
                    <p className="font-semibold text-gray-900">Test Complete</p>
                    <p className="text-sm text-gray-500">
                      {progress.fields_correct !== undefined && `${progress.fields_correct} fields correct`}
                      {progress.fields_wrong !== undefined && progress.fields_wrong > 0 && `, ${progress.fields_wrong} wrong`}
                      {progress.fields_missing !== undefined && progress.fields_missing > 0 && `, ${progress.fields_missing} missing`}
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <span className={`text-3xl font-bold ${
                    progress.overall_score >= 90 ? 'text-green-600' :
                    progress.overall_score >= 70 ? 'text-amber-600' :
                    'text-red-600'
                  }`}>
                    {progress.overall_score}%
                  </span>
                  {progress.overall_grade && (
                    <p className="text-sm font-medium text-gray-600">{progress.overall_grade}</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Error Display */}
          {progress.error && (
            <div className="px-6 py-4 border-t border-red-100 bg-red-50">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
                <div>
                  <p className="font-medium text-red-800">Error</p>
                  <p className="text-sm text-red-600">{progress.error}</p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <style>{`
        @keyframes grid-move {
          0% { background-position: 0 0; }
          100% { background-position: 40px 40px; }
        }
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes draw-cable {
          0% { stroke-dashoffset: 1000; }
          100% { stroke-dashoffset: 0; }
        }
        @keyframes travel-right {
          0% { left: 10%; opacity: 0; transform: scale(0.5); }
          10% { opacity: 1; transform: scale(1); }
          90% { opacity: 1; transform: scale(1); }
          100% { left: 90%; opacity: 0; transform: scale(0.5); }
        }
        @keyframes slide-up {
          from { transform: translateY(100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
        @keyframes slide-up-fade {
          0% { transform: translateY(20px); opacity: 0; }
          20% { transform: translateY(0); opacity: 1; }
          80% { transform: translateY(0); opacity: 1; }
          100% { transform: translateY(-20px); opacity: 0; }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite linear;
        }
        .animate-draw-cable {
          animation: draw-cable 2s ease-out forwards;
          animation-delay: 0.5s;
        }
        .animate-travel-right {
          animation: travel-right 3s infinite linear;
        }
        .animate-slide-up {
          animation: slide-up 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .animate-slide-up-fade {
          animation: slide-up-fade 2.5s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};
