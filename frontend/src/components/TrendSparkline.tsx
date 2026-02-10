import React from 'react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

interface TrendSparklineProps {
  data: (number | null)[];
  color?: string;
  height?: number;
  width?: number;
}

export const TrendSparkline: React.FC<TrendSparklineProps> = ({ 
  data, 
  color = '#10b981', // emerald-500
  height = 20,
  width = 48 
}) => {
  // Filter out nulls for the chart, but we need to maintain index if we want to show gaps
  // For a simple sparkline, we usually just connect the points we have or show gaps.
  // Recharts handles nulls by breaking the line.
  
  const chartData = data.map((val, idx) => ({ i: idx, val }));
  
  // Determine color based on trend. Data is typically newest-first (first = recent, last = older).
  // "Going up" over time = first > last → green. "Going down" = first < last → red.
  const firstVal = data.find(d => d !== null);
  const lastVal = [...data].reverse().find(d => d !== null);
  
  let strokeColor = color;
  if (firstVal !== undefined && lastVal !== undefined && firstVal !== null && lastVal !== null) {
    strokeColor = firstVal >= lastVal ? '#10b981' : '#ef4444'; // up (or flat) = green, down = red
  }

  if (data.every(d => d === null)) return <div className="w-12 h-5" />;

  return (
    <div style={{ width, height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <Line 
            type="monotone" 
            dataKey="val" 
            stroke={strokeColor} 
            strokeWidth={2} 
            dot={false}
            isAnimationActive={false}
          />
          <YAxis domain={['dataMin', 'dataMax']} hide />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
