import React, { useEffect, useState } from 'react';

export const BridgeLoader: React.FC = () => {
  const [messageIndex, setMessageIndex] = useState(0);

  const messages = [
    "Analyzing financial documents...",
    "Constructing data models...",
    "Bridging the gap between PDF and Excel...",
    "Applying financial logic...",
    "Validating extraction results...",
    "Polishing the numbers...",
    "Finalizing the spread..."
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % messages.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

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
          <p key={messageIndex} className="text-gray-500 font-medium animate-slide-up-fade">
            {messages[messageIndex]}
          </p>
        </div>
      </div>

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
