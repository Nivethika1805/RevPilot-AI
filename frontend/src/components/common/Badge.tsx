import React from 'react';
import { AlertCircle, AlertTriangle, CheckCircle2, Info, ShieldAlert } from 'lucide-react';

interface RiskBadgeProps {
  category: 'Low' | 'Medium' | 'High' | 'Critical' | string;
  score?: number;
  size?: 'sm' | 'md' | 'lg';
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ category, score, size = 'md' }) => {
  const cat = category.toLowerCase();

  let colorClasses = 'bg-emerald-950/80 text-emerald-400 border-emerald-700/50';
  let Icon = CheckCircle2;

  if (cat === 'critical') {
    colorClasses = 'bg-rose-950/80 text-rose-300 border-rose-700/60 shadow-[0_0_12px_rgba(225,29,72,0.25)]';
    Icon = ShieldAlert;
  } else if (cat === 'high') {
    colorClasses = 'bg-amber-950/80 text-amber-300 border-amber-700/50';
    Icon = AlertTriangle;
  } else if (cat === 'medium') {
    colorClasses = 'bg-yellow-950/70 text-yellow-300 border-yellow-700/40';
    Icon = AlertCircle;
  }

  const sizeClasses = size === 'sm' ? 'text-xs px-2 py-0.5' : size === 'lg' ? 'text-sm px-3.5 py-1.5' : 'text-xs px-2.5 py-1';

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-md border ${colorClasses} ${sizeClasses}`}>
      <Icon className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />
      <span>{category}</span>
      {score !== undefined && (
        <span className="font-mono opacity-80 pl-1 border-l border-current/20">{Math.round(score)}</span>
      )}
    </span>
  );
};

export const SyntheticBadge: React.FC = () => (
  <span className="inline-flex items-center gap-1 text-[11px] font-semibold tracking-wider uppercase px-2.5 py-0.5 rounded border border-indigo-500/40 bg-indigo-950/60 text-indigo-300">
    <Info className="w-3 h-3 text-indigo-400" />
    <span>Synthetic Demo Data</span>
  </span>
);

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const s = status.toLowerCase();
  let classes = 'bg-slate-800 text-slate-300 border-slate-700';

  if (s === 'open' || s === 'recommended' || s === 'in_progress') {
    classes = 'bg-blue-950/70 text-blue-300 border-blue-700/50';
  } else if (s === 'completed' || s === 'accepted' || s === 'resolved' || s === 'won') {
    classes = 'bg-emerald-950/70 text-emerald-300 border-emerald-700/50';
  } else if (s === 'overridden' || s === 'pending') {
    classes = 'bg-purple-950/70 text-purple-300 border-purple-700/50';
  } else if (s === 'unassigned_review' || s === 'critical' || s === 'lost') {
    classes = 'bg-rose-950/70 text-rose-300 border-rose-700/50';
  }

  return (
    <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded border ${classes}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
};

export const PriorityBadge: React.FC<{ priority: string }> = ({ priority }) => {
  const p = (priority || '').toLowerCase();
  let classes = 'bg-slate-800 text-slate-300 border-slate-700';

  if (p === 'critical') {
    classes = 'bg-rose-950/80 text-rose-300 border-rose-700/60';
  } else if (p === 'high') {
    classes = 'bg-amber-950/80 text-amber-300 border-amber-700/50';
  } else if (p === 'medium') {
    classes = 'bg-blue-950/70 text-blue-300 border-blue-700/40';
  } else if (p === 'low') {
    classes = 'bg-slate-800/80 text-slate-400 border-slate-700';
  }

  return (
    <span className={`inline-flex items-center text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${classes}`}>
      {priority}
    </span>
  );
};

