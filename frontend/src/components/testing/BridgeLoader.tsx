import React, { useEffect, useState, useRef } from 'react';
import { FileText, CheckCircle, AlertCircle, Loader2, Clock, Zap, TrendingUp, Target } from 'lucide-react';

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

interface ProgressEvent {
  timestamp: number;
  filename: string;
  phase: string;
  duration?: number;
  status: 'running' | 'success' | 'error';
  message: string;
  score?: number;
}

interface Target {
  x: number;
  y: number;
  size: number;
  speed: number;
  color: string;
  points: number;
}

export const BridgeLoader: React.FC<BridgeLoaderProps> = ({ progress }) => {
  // Game state
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [gameScore, setGameScore] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const gameStateRef = useRef({
    targets: [] as Target[],
    lastSpawn: 0,
    animationFrame: 0,
  });

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

  // Simple target shooting game
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = 800;
    canvas.height = 400;

    const spawnTarget = () => {
      const colors = ['#8b5cf6', '#06b6d4', '#10b981', '#f59e0b', '#ef4444'];
      const target: Target = {
        x: Math.random() * (canvas.width - 60) + 30,
        y: -30,
        size: 30 + Math.random() * 20,
        speed: 1 + Math.random() * 2,
        color: colors[Math.floor(Math.random() * colors.length)],
        points: Math.floor(50 / (30 + Math.random() * 20)),
      };
      gameStateRef.current.targets.push(target);
    };

    const handleClick = (e: MouseEvent) => {
      if (!isPlaying) {
        setIsPlaying(true);
        return;
      }

      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      // Check if clicked on any target
      gameStateRef.current.targets = gameStateRef.current.targets.filter(target => {
        const distance = Math.sqrt(
          Math.pow(x - target.x, 2) + Math.pow(y - target.y, 2)
        );

        if (distance < target.size) {
          setGameScore(prev => prev + target.points);
          
          // Visual feedback
          ctx.save();
          ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
          ctx.beginPath();
          ctx.arc(target.x, target.y, target.size * 1.5, 0, Math.PI * 2);
          ctx.fill();
          ctx.restore();
          
          return false; // Remove target
        }
        return true; // Keep target
      });
    };

    canvas.addEventListener('click', handleClick);

    const gameLoop = () => {
      // Clear canvas
      ctx.fillStyle = 'rgba(15, 23, 42, 1)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Draw grid background
      ctx.strokeStyle = 'rgba(139, 92, 246, 0.1)';
      ctx.lineWidth = 1;
      for (let i = 0; i < canvas.width; i += 40) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, canvas.height);
        ctx.stroke();
      }
      for (let i = 0; i < canvas.height; i += 40) {
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(canvas.width, i);
        ctx.stroke();
      }

      if (isPlaying) {
        // Spawn targets
        const now = Date.now();
        if (now - gameStateRef.current.lastSpawn > 1000) {
          spawnTarget();
          gameStateRef.current.lastSpawn = now;
        }

        // Update and draw targets
        gameStateRef.current.targets = gameStateRef.current.targets.filter(target => {
          target.y += target.speed;

          // Draw target
          ctx.save();
          
          // Outer glow
          const gradient = ctx.createRadialGradient(
            target.x, target.y, 0,
            target.x, target.y, target.size
          );
          gradient.addColorStop(0, target.color);
          gradient.addColorStop(1, target.color + '00');
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.arc(target.x, target.y, target.size * 1.3, 0, Math.PI * 2);
          ctx.fill();

          // Target circle
          ctx.fillStyle = target.color;
          ctx.beginPath();
          ctx.arc(target.x, target.y, target.size, 0, Math.PI * 2);
          ctx.fill();

          // Center dot
          ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
          ctx.beginPath();
          ctx.arc(target.x, target.y, target.size * 0.3, 0, Math.PI * 2);
          ctx.fill();

          // Points text
          ctx.fillStyle = 'white';
          ctx.font = 'bold 14px sans-serif';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText('+' + target.points, target.x, target.y);

          ctx.restore();

          // Remove if off screen
          return target.y < canvas.height + 50;
        });
      } else {
        // Draw start message
        ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
        ctx.font = 'bold 32px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('🎯 Click to Start!', canvas.width / 2, canvas.height / 2 - 20);
        
        ctx.font = '16px sans-serif';
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.fillText('Click falling targets to score points', canvas.width / 2, canvas.height / 2 + 20);
      }

      gameStateRef.current.animationFrame = requestAnimationFrame(gameLoop);
    };

    gameLoop();

    return () => {
      canvas.removeEventListener('click', handleClick);
      if (gameStateRef.current.animationFrame) {
        cancelAnimationFrame(gameStateRef.current.animationFrame);
      }
    };
  }, [isPlaying]);

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
          <div className="absolute top-8 left-8 right-8 flex items-center justify-between z-10">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">
                Target Shooter
              </h2>
              <p className="text-sm text-gray-400">
                Click the falling targets to score points!
              </p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-violet-400">{gameScore}</div>
              <div className="text-xs text-gray-400">Score</div>
            </div>
          </div>

          {/* Game Canvas */}
          <canvas
            ref={canvasRef}
            className="rounded-2xl shadow-2xl border-4 border-white/10 cursor-crosshair"
            style={{ imageRendering: 'crisp-edges' }}
          />

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
