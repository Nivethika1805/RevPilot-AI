import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  DollarSign, Briefcase, AlertTriangle, MessageSquare, Clock,
  TrendingUp, Users, ArrowRight, CheckCircle2, ShieldAlert
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, Cell, PieChart, Pie
} from 'recharts';
import { apiClient } from '../api/client';
import { DashboardMetrics } from '../types';
import { RiskBadge, StatusBadge } from '../components/common/Badge';
import { InfoTooltip } from '../components/common/Tooltip';
import { TableSkeleton, CardSkeleton } from '../components/common/Skeleton';

import { useQuery } from '@tanstack/react-query';

export const CommandCenter: React.FC = () => {
  const navigate = useNavigate();

  const { data: metrics, isLoading: loading, error, refetch } = useQuery<DashboardMetrics>({
    queryKey: ['dashboardMetrics'],
    queryFn: () => apiClient.getDashboardMetrics(),
    refetchInterval: 15000,
  });

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(val || 0);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <TableSkeleton rows={6} />
      </div>
    );
  }

  if (error || !metrics) {
    const errorMsg = (error as any)?.response?.data?.message || (error as any)?.message || 'Failed to load dashboard metrics';
    return (
      <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-100">Unable to load metrics</h3>
        <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">{errorMsg}</p>
        <button
          onClick={() => refetch()}
          className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-xs font-medium rounded-lg text-white transition"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  // Chart data
  const riskChartData = [
    { name: 'Low', count: metrics.risk_distribution['Low'] || 0, color: '#10b981' },
    { name: 'Medium', count: metrics.risk_distribution['Medium'] || 0, color: '#f59e0b' },
    { name: 'High', count: metrics.risk_distribution['High'] || 0, color: '#f97316' },
    { name: 'Critical', count: metrics.risk_distribution['Critical'] || 0, color: '#ef4444' },
  ];

  const stageChartData = Object.entries(metrics.stage_distribution).map(([stage, info]) => ({
    stage,
    count: info.count,
    value: Math.round(info.value / 1000), // in $k
  }));

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Revenue Command Center
            <span className="text-xs font-normal text-slate-400 bg-slate-900 px-2.5 py-0.5 rounded-full border border-slate-800">
              Live Pipeline Overview
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Real-time pipeline posture, rule-based risk distribution, and manager action prioritization.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/findings')}
            className="px-3.5 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/40 rounded-lg text-xs font-medium flex items-center gap-1.5 transition"
          >
            <span>View Evidenced Findings</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Top 5 Executive Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Pipeline Value */}
        <div
          onClick={() => navigate('/deals')}
          className="glass-card p-4 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Open Pipeline</span>
            <DollarSign className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-white mt-2">
            {formatCurrency(metrics.total_open_pipeline_value)}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
            <span>{metrics.total_open_deals} open deals in pipeline</span>
          </div>
        </div>

        {/* At-Risk Deals */}
        <div
          onClick={() => navigate('/deals?risk_category=at_risk')}
          className="glass-card p-4 rounded-xl border border-rose-900/40 hover:border-rose-700/60 cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="flex items-center gap-1">
              At-Risk Deals
              <InfoTooltip content="Deals classified as High (50-74) or Critical (75-100) on our rule-based risk index. Measures detected risk factors, not statistical probability." />
            </span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-xl font-bold text-rose-300 mt-2">
            {metrics.at_risk_deals_count} Deals
          </div>
          <div className="text-[11px] text-rose-400/80 mt-1">High &amp; Critical risk index</div>
        </div>

        {/* High-Priority Conversations */}
        <div
          onClick={() => navigate('/inbox?urgency=high')}
          className="glass-card p-4 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>High Urgency Convs</span>
            <MessageSquare className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-xl font-bold text-white mt-2">
            {metrics.high_priority_conversations_count}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Active customer dialogues</div>
        </div>

        {/* Overdue Follow-ups */}
        <div
          onClick={() => navigate('/actions')}
          className="glass-card p-4 rounded-xl border border-amber-900/40 hover:border-amber-700/60 cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span className="flex items-center gap-1">
              Overdue Actions
              <InfoTooltip content="Actions with a due date earlier than the current pinned As-Of date (Oct 20, 2026)." />
            </span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-xl font-bold text-amber-300 mt-2">
            {metrics.overdue_follow_ups_count} Overdue
          </div>
          <div className="text-[11px] text-amber-400/80 mt-1">Requires immediate follow-up</div>
        </div>

        {/* Open Alerts */}
        <div
          onClick={() => navigate('/deals')}
          className="glass-card p-4 rounded-xl border border-slate-800 hover:border-slate-700 cursor-pointer transition"
        >
          <div className="flex items-center justify-between text-slate-400 text-xs">
            <span>Pending Alerts</span>
            <AlertTriangle className="w-4 h-4 text-yellow-400" />
          </div>
          <div className="text-xl font-bold text-white mt-2">
            {metrics.recent_alerts.length}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Requiring acknowledgment</div>
        </div>
      </div>

      {/* Charts Section: Risk Distribution & Pipeline Stages */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Distribution Bar Chart */}
        <div className="glass-panel p-5 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-1.5">
                Rule-Based Risk Distribution
                <InfoTooltip content="Distribution of current risk assessment scores across open deals. Calculated purely deterministically from active signals." />
              </h2>
              <p className="text-[11px] text-slate-400">Deals by risk category</p>
            </div>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={riskChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} allowDecimals={false} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }}
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {riskChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Stage Value Chart */}
        <div className="glass-panel p-5 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-1.5">
                Pipeline Stage Breakdown
                <InfoTooltip content="Active deal count and total value per sales milestone." />
              </h2>
              <p className="text-[11px] text-slate-400">Total pipeline value ($k) per stage</p>
            </div>
          </div>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stageChartData} layout="vertical" margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                <XAxis type="number" stroke="#64748b" fontSize={11} unit="k" tickLine={false} />
                <YAxis type="category" dataKey="stage" stroke="#64748b" fontSize={11} tickLine={false} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }}
                  formatter={(val: any) => [`$${val}k`, 'Value']}
                />
                <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Prioritized "What Should I Do Today?" Queue Preview */}
      <div className="glass-panel p-5 rounded-xl">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-blue-400" />
              Prioritized Action Queue ("What Should I Do Today?")
              <InfoTooltip content="Actions automatically generated from detected risk signals, unassigned conversations, and deadlines. Ranked deterministically by priority, due date, deal value, and risk index." />
            </h2>
            <p className="text-[11px] text-slate-400">Top ranked recommendations for immediate resolution</p>
          </div>
          <button
            onClick={() => navigate('/actions')}
            className="text-xs text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1 transition"
          >
            <span>Full Queue ({metrics.what_should_i_do_today.length})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="divide-y divide-slate-800/80">
          {metrics.what_should_i_do_today.slice(0, 5).map((action) => (
            <div
              key={action.id}
              className="py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-900/40 px-2 rounded-lg transition"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${
                    action.priority === 'critical'
                      ? 'bg-rose-950/80 text-rose-300 border-rose-800/60'
                      : action.priority === 'high'
                      ? 'bg-amber-950/80 text-amber-300 border-amber-800/60'
                      : 'bg-blue-950/80 text-blue-300 border-blue-800/60'
                  }`}>
                    {action.priority}
                  </span>
                  <span className="text-xs font-semibold text-white truncate">{action.title}</span>
                  <span className="text-[11px] text-slate-400 truncate">({action.deal_code} — {action.deal_name})</span>
                </div>
                <p className="text-xs text-slate-400 mt-1 line-clamp-1">{action.reason}</p>
              </div>

              <div className="flex items-center gap-3 shrink-0">
                <div className="text-right">
                  <div className="text-[11px] text-slate-300">{action.owner_name}</div>
                  <div className="text-[10px] text-slate-400">
                    Due: {action.due_date ? new Date(action.due_date).toLocaleDateString() : 'Immediate'}
                  </div>
                </div>
                <button
                  onClick={() => navigate(`/deals/${action.deal_id}`)}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 rounded border border-slate-700 transition"
                >
                  Inspect Deal
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Two columns: Team Performance & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Team Performance Table */}
        <div className="glass-panel p-5 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Users className="w-4 h-4 text-blue-400" />
              Team Performance Indicators
            </h2>
            <span className="text-[11px] text-slate-400">Account Executives & Specialists</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-slate-400 border-b border-slate-800 text-[11px]">
                <tr>
                  <th className="pb-2 font-medium">Representative</th>
                  <th className="pb-2 font-medium text-right">Open Deals</th>
                  <th className="pb-2 font-medium text-right">Pipeline</th>
                  <th className="pb-2 font-medium text-right">Overdue</th>
                  <th className="pb-2 font-medium text-right">Completed</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {metrics.team_performance.map((rep) => (
                  <tr key={rep.rep_name} className="hover:bg-slate-900/40">
                    <td className="py-2.5 font-medium text-slate-200">{rep.rep_name}</td>
                    <td className="py-2.5 text-right font-mono text-slate-300">{rep.open_deals}</td>
                    <td className="py-2.5 text-right font-mono text-emerald-400">
                      ${(rep.pipeline_value / 1000).toFixed(0)}k
                    </td>
                    <td className={`py-2.5 text-right font-mono font-medium ${rep.overdue_actions > 0 ? 'text-amber-400' : 'text-slate-400'}`}>
                      {rep.overdue_actions}
                    </td>
                    <td className="py-2.5 text-right font-mono text-blue-400">{rep.completed_actions}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Activity Feed */}
        <div className="glass-panel p-5 rounded-xl">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-400" />
              Recent Sales Activity Stream
            </h2>
            <span className="text-[11px] text-slate-400">Last 8 logged events</span>
          </div>

          <div className="space-y-3">
            {metrics.recent_activities.map((act) => (
              <div key={act.id} className="flex items-start gap-3 text-xs">
                <span className="font-mono text-[10px] text-slate-400 bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800 shrink-0">
                  {act.source_ref}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="text-slate-300 line-clamp-1">{act.detail}</div>
                  <div className="text-[10px] text-slate-400 mt-0.5 flex items-center gap-2">
                    <span>{act.user_name}</span>
                    <span>•</span>
                    <span>{new Date(act.occurred_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
