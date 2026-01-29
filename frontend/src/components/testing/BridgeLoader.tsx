import React, { useEffect, useState, useRef, useCallback } from 'react';
import { FileText, CheckCircle, AlertCircle, Loader2, Clock, Zap, TrendingUp } from 'lucide-react';

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
  file_extraction_time?: number;
}

interface BridgeLoaderProps {
  progress?: TestProgress | null;
}

interface GameState {
  position: number; // 0-100
  velocity: number;
  score: number;
  obstacles: { position: number; gap: number }[];
}

interface ProgressEvent {
  timestamp: number;
  filename: string;
  phase: string;
  duration?: number;
  status: 'running' | 'success' | 'error';
  message: string;
  score?: number;
}

export const BridgeLoader: React.FC<BridgeLoaderProps> = ({ progress }) => {
  // Game state
  const [gameState, setGameState] = useState<GameState>({
    position: 50,
    velocity: 0,
    score: 0,
    obstacles: [],
  });
  const [isGameActive, setIsGameActive] = useState(false);
  const gameLoopRef = useRef<number>();
  const keysPressed = useRef<Set<string>>(new Set());

  // Progress tracking
  const [progressEvents, setProgressEvents] = useState<ProgressEvent[]>([]);
  const progressContainerRef = useRef<HTMLDivElement>(null);

  // Track progress history
  useEffect(() => {
    if (progress) {
      const event: ProgressEvent = {
        timestamp: Date.now(),
        filename: progress.current_filename || 'System',
        phase: progress.phase,
        duration: progress.file_extraction_time,
        status: progress.phase === 'file_complete' ? 'success' : 
                progress.phase === 'file_error' ? 'error' : 'running',
        message: progress.message,
        score: progress.file_score,
      };
      
      setProgressEvents(prev => [...prev, event]);
      
      // Auto-scroll to bottom
      setTimeout(() => {
        if (progressContainerRef.current) {
          progressContainerRef.current.scrollTop = progressContainerRef.current.scrollHeight;
        }
      }, 100);
    }
  }, [progress]);

  // Game logic
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['ArrowUp', 'ArrowDown', 'Space', ' '].includes(e.key)) {
        e.preventDefault();
        keysPressed.current.add(e.key);
        setIsGameActive(true);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      keysPressed.current.delete(e.key);
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  // Game loop
  useEffect(() => {
    if (!isGameActive) return;

    const gameLoop = () => {
      setGameState(prev => {
        let newVelocity = prev.velocity;
        let newPosition = prev.position;

        // Handle input
        if (keysPressed.current.has('ArrowUp') || keysPressed.current.has('Space') || keysPressed.current.has(' ')) {
          newVelocity = Math.max(newVelocity - 0.8, -5);
        } else {
          newVelocity = Math.min(newVelocity + 0.4, 5);
        }

        // Update position
        newPosition = Math.max(0, Math.min(100, newPosition + newVelocity));

        // Generate new obstacles occasionally
        let newObstacles = prev.obstacles.map(obs => ({
          ...obs,
          position: obs.position - 2,
        })).filter(obs => obs.position > -10);

        if (Math.random() < 0.02 && newObstacles.length < 3) {
          newObstacles.push({
            position: 110,
            gap: 30 + Math.random() * 20,
          });
        }

        // Check collisions & update score
        let newScore = prev.score;
        newObstacles.forEach(obs => {
          if (obs.position > 48 && obs.position < 52) {
            const gapStart = 50 - obs.gap / 2;
            const gapEnd = 50 + obs.gap / 2;
            if (newPosition < gapStart || newPosition > gapEnd) {
              // Hit obstacle - reset
              newPosition = 50;
              newVelocity = 0;
            } else if (obs.position === 50) {
              newScore += 10;
            }
          }
        });

        return {
          position: newPosition,
          velocity: newVelocity,
          score: newScore,
          obstacles: newObstacles,
        };
      });

      gameLoopRef.current = requestAnimationFrame(gameLoop);
    };

    gameLoopRef.current = requestAnimationFrame(gameLoop);

    return () => {
      if (gameLoopRef.current) {
        cancelAnimationFrame(gameLoopRef.current);
      }
    };
  }, [isGameActive]);

  const formatTime = (seconds?: number) => {
    if (!seconds) return '0s';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const getPhaseIcon = (phase: string, status: string) => {
    if (status === 'success') return <CheckCircle className="w-4 h-4 text-green-500" />;
    if (status === 'error') return <AlertCircle className="w-4 h-4 text-red-500" />;
    return <Loader2 className="w-4 h-4 text-violet-500 animate-spin" />;
  };

  const progressPercent = progress && progress.total_files && progress.files_completed !== undefined
    ? Math.round((progress.files_completed / progress.total_files) * 100)
    : 0;

  return (
    <div className="fixed inset-0 z-50 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-hidden">
      <div className="h-full flex flex-col lg:flex-row">
        {/* Left Side - Interactive Game */}
        <div className="flex-1 flex flex-col items-center justify-center p-8 relative">
          {/* Game Title */}
          <div className="absolute top-8 left-8 right-8 flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">
                Bridge Flight Challenge
              </h2>
              <p className="text-sm text-gray-400">
                Press <kbd className="px-2 py-1 bg-white/10 rounded text-xs">SPACE</kbd> or <kbd className="px-2 py-1 bg-white/10 rounded text-xs">↑</kbd> to fly up!
              </p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-violet-400">{gameState.score}</div>
              <div className="text-xs text-gray-400">Score</div>
            </div>
          </div>

          {/* Game Canvas */}
          <div className="relative w-full max-w-4xl h-96 bg-gradient-to-b from-sky-900 to-sky-700 rounded-2xl overflow-hidden shadow-2xl border-4 border-white/10">
            {/* Background elements */}
            <div className="absolute inset-0 opacity-20" 
                 style={{ 
                   backgroundImage: 'linear-gradient(#4f46e5 1px, transparent 1px), linear-gradient(90deg, #4f46e5 1px, transparent 1px)', 
                   backgroundSize: '40px 40px',
                   animation: 'grid-move 20s linear infinite'
                 }} 
            />

            {/* Player (flying bridge element) */}
            <div 
              className="absolute left-1/4 w-12 h-8 transition-all duration-100"
              style={{ 
                top: `${gameState.position}%`,
                transform: 'translateY(-50%)',
              }}
            >
              <div className="relative">
                <div className="absolute inset-0 bg-gradient-to-r from-violet-500 to-purple-600 rounded-lg shadow-lg shadow-violet-500/50 animate-pulse" />
                <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-0 h-0 border-t-4 border-t-transparent border-b-4 border-b-transparent border-l-8 border-l-purple-600" />
              </div>
            </div>

            {/* Obstacles */}
            {gameState.obstacles.map((obs, idx) => (
              <div key={idx} className="absolute" style={{ left: `${obs.position}%` }}>
                {/* Top obstacle */}
                <div 
                  className="absolute top-0 w-12 bg-gradient-to-b from-emerald-600 to-emerald-700 rounded-b-lg border-2 border-emerald-500/50"
                  style={{ height: `${50 - obs.gap / 2}%` }}
                />
                {/* Bottom obstacle */}
                <div 
                  className="absolute bottom-0 w-12 bg-gradient-to-t from-emerald-600 to-emerald-700 rounded-t-lg border-2 border-emerald-500/50"
                  style={{ height: `${50 - obs.gap / 2}%` }}
                />
              </div>
            ))}

            {/* Start prompt */}
            {!isGameActive && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 backdrop-blur-sm">
                <div className="text-center">
                  <div className="text-6xl mb-4 animate-bounce">🎮</div>
                  <p className="text-white text-xl font-semibold mb-2">Press SPACE or ↑ to Start</p>
                  <p className="text-gray-300 text-sm">Fly through the gaps while tests run!</p>
                </div>
              </div>
            )}
          </div>

          {/* Progress Summary Bar */}
          {progress && progress.total_files ? (
            <div className="mt-8 w-full max-w-4xl">
              <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-white font-semibold">Overall Progress</span>
                  <span className="text-violet-300 font-bold text-lg">{progressPercent}%</span>
                </div>
                <div className="h-3 bg-black/30 rounded-full overflow-hidden mb-3">
                  <div 
                    className="h-full bg-gradient-to-r from-violet-500 via-purple-500 to-blue-500 rounded-full transition-all duration-500"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-white">{progress.files_completed || 0}</div>
                    <div className="text-gray-400">Completed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-violet-300">{progress.total_files || 0}</div>
                    <div className="text-gray-400">Total Files</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-300">{formatTime(progress.elapsed_seconds)}</div>
                    <div className="text-gray-400">Elapsed</div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="mt-8 w-full max-w-4xl">
              <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
                <div className="flex items-center justify-center gap-3 text-gray-300">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Connecting to test runner...</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right Side - Detailed Progress Timeline */}
        <div className="w-full lg:w-96 xl:w-[32rem] bg-slate-950/80 backdrop-blur-xl border-l border-white/10 flex flex-col">
          {/* Header */}
          <div className="px-6 py-4 border-b border-white/10">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-violet-400" />
              Execution Trace
            </h3>
            <p className="text-xs text-gray-400 mt-1">Real-time processing updates</p>
          </div>

          {/* Progress Events Timeline */}
          <div 
            ref={progressContainerRef}
            className="flex-1 overflow-y-auto px-4 py-4 space-y-3"
          >
            {progressEvents.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <Loader2 className="w-8 h-8 animate-spin mb-2" />
                <p className="text-sm">Waiting for progress updates...</p>
              </div>
            ) : (
              progressEvents.map((event, idx) => {
                const isLast = idx === progressEvents.length - 1;
                const timeSinceStart = progressEvents[0] 
                  ? ((event.timestamp - progressEvents[0].timestamp) / 1000).toFixed(1)
                  : '0.0';

                return (
                  <div 
                    key={idx}
                    className={`relative pl-8 pb-6 ${isLast ? 'animate-slide-in-right' : ''}`}
                  >
                    {/* Timeline line */}
                    {idx < progressEvents.length - 1 && (
                      <div className="absolute left-3 top-6 bottom-0 w-0.5 bg-gradient-to-b from-violet-500/50 to-transparent" />
                    )}

                    {/* Event marker */}
                    <div className="absolute left-0 top-1">
                      {getPhaseIcon(event.phase, event.status)}
                    </div>

                    {/* Event content */}
                    <div className={`rounded-lg p-3 border transition-all ${
                      event.status === 'success' 
                        ? 'bg-green-500/10 border-green-500/30' 
                        : event.status === 'error'
                          ? 'bg-red-500/10 border-red-500/30'
                          : 'bg-violet-500/10 border-violet-500/30'
                    }`}>
                      <div className="flex items-start justify-between mb-1">
                        <span className="text-white font-medium text-sm truncate flex-1">
                          {event.filename}
                        </span>
                        <span className="text-xs text-gray-400 ml-2 flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {timeSinceStart}s
                        </span>
                      </div>
                      
                      <div className="text-xs text-gray-300 mb-2">
                        {event.message}
                      </div>

                      {event.duration !== undefined && (
                        <div className="flex items-center gap-2 text-xs">
                          <span className="text-gray-400">Duration:</span>
                          <span className="text-violet-300 font-mono">{event.duration.toFixed(1)}s</span>
                        </div>
                      )}

                      {event.score !== undefined && (
                        <div className="flex items-center gap-2 text-xs mt-1">
                          <TrendingUp className="w-3 h-3 text-green-400" />
                          <span className="text-green-300 font-semibold">{event.score.toFixed(1)}%</span>
                        </div>
                      )}

                      <div className="mt-2 pt-2 border-t border-white/10">
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          event.status === 'success'
                            ? 'bg-green-500/20 text-green-300'
                            : event.status === 'error'
                              ? 'bg-red-500/20 text-red-300'
                              : 'bg-violet-500/20 text-violet-300'
                        }`}>
                          {event.phase.replace('_', ' ')}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Current Status Footer */}
          {progress && (
            <div className="px-6 py-4 border-t border-white/10 bg-slate-950/50">
              <div className="flex items-center gap-3">
                <div className={`w-2 h-2 rounded-full ${
                  progress.phase === 'complete' ? 'bg-green-400' : 'bg-violet-400 animate-pulse'
                }`} />
                <div className="flex-1 min-w-0">
                  <p className="text-white text-sm font-medium truncate">
                    {progress.current_filename || 'Processing...'}
                  </p>
                  <p className="text-gray-400 text-xs capitalize">
                    {progress.phase.replace('_', ' ')}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes grid-move {
          0% { background-position: 0 0; }
          100% { background-position: 40px 40px; }
        }
        @keyframes slide-in-right {
          from {
            opacity: 0;
            transform: translateX(20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        .animate-slide-in-right {
          animation: slide-in-right 0.3s ease-out;
        }
      `}</style>
    </div>
  );
};
