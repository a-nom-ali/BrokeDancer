/**
 * Skeleton Components
 *
 * Skeleton loading placeholders for various UI elements.
 */

import React from 'react';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className = '' }) => (
  <div className={`animate-pulse bg-gray-700 rounded ${className}`} />
);

export const SkeletonCard: React.FC = () => (
  <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
    <Skeleton className="h-4 w-1/3 mb-3" />
    <Skeleton className="h-8 w-1/2 mb-2" />
    <Skeleton className="h-3 w-2/3" />
  </div>
);

export const SkeletonMetricCard: React.FC = () => (
  <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
    <div className="flex items-center justify-between mb-2">
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-5 w-5 rounded" />
    </div>
    <Skeleton className="h-8 w-16 mb-1" />
    <Skeleton className="h-3 w-24" />
  </div>
);

export const SkeletonRow: React.FC = () => (
  <div className="flex items-center gap-4 p-3 border-b border-gray-700">
    <Skeleton className="h-4 w-24" />
    <Skeleton className="h-4 w-32" />
    <Skeleton className="h-4 w-20" />
    <Skeleton className="h-4 w-16" />
  </div>
);

export const SkeletonEventCard: React.FC = () => (
  <div className="bg-gray-800 rounded-lg border border-gray-700 p-3">
    <div className="flex items-center justify-between mb-2">
      <Skeleton className="h-5 w-32" />
      <Skeleton className="h-4 w-20" />
    </div>
    <Skeleton className="h-3 w-full mb-1" />
    <Skeleton className="h-3 w-2/3" />
  </div>
);

export const SkeletonWorkflowNode: React.FC = () => (
  <div className="bg-gray-800 rounded-lg border border-gray-600 p-3 min-w-[150px]">
    <div className="flex items-center justify-between">
      <Skeleton className="h-4 w-20" />
      <Skeleton className="h-4 w-4 rounded-full" />
    </div>
    <Skeleton className="h-3 w-16 mt-2" />
  </div>
);

interface SkeletonGridProps {
  count?: number;
  columns?: number;
}

export const SkeletonMetricGrid: React.FC<SkeletonGridProps> = ({
  count = 4,
  columns = 4,
}) => (
  <div className={`grid grid-cols-1 md:grid-cols-2 lg:grid-cols-${columns} gap-4`}>
    {Array.from({ length: count }).map((_, i) => (
      <SkeletonMetricCard key={i} />
    ))}
  </div>
);

export const SkeletonTable: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
    <div className="p-3 border-b border-gray-700 bg-gray-750">
      <Skeleton className="h-4 w-48" />
    </div>
    {Array.from({ length: rows }).map((_, i) => (
      <SkeletonRow key={i} />
    ))}
  </div>
);

export default Skeleton;
