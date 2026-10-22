import React from 'react';

export const TableSkeleton: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="w-full space-y-3 animate-pulse p-4">
    <div className="h-8 bg-slate-800/60 rounded w-full mb-4"></div>
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="h-12 bg-slate-800/40 rounded flex items-center px-4 gap-4">
        <div className="h-4 bg-slate-700/60 rounded w-1/4"></div>
        <div className="h-4 bg-slate-700/40 rounded w-1/4"></div>
        <div className="h-4 bg-slate-700/40 rounded w-1/4"></div>
        <div className="h-4 bg-slate-700/50 rounded w-1/6"></div>
      </div>
    ))}
  </div>
);

export const CardSkeleton: React.FC = () => (
  <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 animate-pulse">
    <div className="h-4 bg-slate-800 rounded w-1/3"></div>
    <div className="h-8 bg-slate-800/80 rounded w-1/2"></div>
    <div className="h-3 bg-slate-800/60 rounded w-full"></div>
  </div>
);
