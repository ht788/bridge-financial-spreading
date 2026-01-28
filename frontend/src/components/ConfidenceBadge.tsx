import React from 'react';
import { getConfidenceLevel, getConfidenceColor, getConfidenceBgColor } from '../utils';
import clsx from 'clsx';

interface ConfidenceBadgeProps {
  confidence: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  compact?: boolean;
}

export const ConfidenceBadge: React.FC<ConfidenceBadgeProps> = ({
  confidence,
  size = 'md',
  showLabel = false,
  compact = false,
}) => {
  const level = getConfidenceLevel(confidence);
  const percentage = Math.round(confidence * 100);
  
  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4',
  };

  // Compact mode uses smaller size
  const effectiveSize = compact ? 'sm' : size;

  return (
    <div className={clsx('flex items-center', compact ? 'gap-1' : 'gap-2')}>
      <div
        className={clsx(
          'rounded-full flex-shrink-0',
          sizeClasses[effectiveSize],
          level === 'high' && 'bg-confidence-high',
          level === 'medium' && 'bg-confidence-medium',
          level === 'low' && 'bg-confidence-low'
        )}
        title={`Confidence: ${percentage}%`}
      />
      {showLabel && (
        <span className={clsx('font-medium', compact ? 'text-[10px]' : 'text-xs', getConfidenceColor(confidence))}>
          {percentage}%
        </span>
      )}
    </div>
  );
};
