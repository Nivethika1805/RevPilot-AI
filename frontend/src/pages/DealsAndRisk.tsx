import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Briefcase, Search, Filter, ShieldAlert, ArrowUpRight, DollarSign,
  TrendingDown, CheckCircle2, ChevronRight, AlertCircle, Edit3
} from 'lucide-react';
import { apiClient } from '../api/client';
import { Deal } from '../types';
import { RiskBadge, StatusBadge } from '../components/common/Badge';
import { TableSkeleton } from '../components/common/Skeleton';
import { InfoTooltip } from '../components/common/Tooltip';

export const DealsAndRisk: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [deals, setDeals] = useState<Deal[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters
  const qParam = searchParams.get('q') || '';
  const riskParam = searchParams.get('risk_category') || '';
  const stageParam = searchParams.get('stage') || '';

  const fetchDeals = async () => {
    setLoading(true);
    try {
      const res = await apiClient.getDeals({
        q: qParam || undefined,
        risk_category: riskParam || undefined,
        stage: stageParam || undefined,
        sort_by: 'current_risk_score',
        sort_order: 'desc',
        limit: 50,
      });
      setDeals(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load deals', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
  }, [qParam, riskParam, stageParam]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Deals & Risk Intelligence
            <span className="text-xs font-normal text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              {total} Pipeline Deals
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Audit pipeline health, review transparent risk signals, inspect field provenance, and drill into deal cockpits.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <button
            onClick={() => {
              searchParams.delete('risk_category');
              searchParams.delete('stage');
              setSearchParams(searchParams);
            }}
            className={`px-2.5 py-1 rounded-md border text-xs font-medium transition ${
              !riskParam && !stageParam ? 'bg-blue-600 text-white border-blue-500' : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
            }`}
          >
            All Deals
          </button>
          <button
            onClick={() => {
              searchParams.set('risk_category', 'critical');
              setSearchParams(searchParams);
            }}
            className={`px-2.5 py-1 rounded-md border text-xs font-medium transition ${
              riskParam === 'critical' ? 'bg-rose-950 text-rose-300 border-rose-800' : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
            }`}
          >
            Critical Risk (75-100)
          </button>
          <button
            onClick={() => {
              searchParams.set('risk_category', 'high');
              setSearchParams(searchParams);
            }}
            className={`px-2.5 py-1 rounded-md border text-xs font-medium transition ${
              riskParam === 'high' ? 'bg-amber-950 text-amber-300 border-amber-800' : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
            }`}
          >
            High Risk (50-74)
          </button>
          <button
            onClick={() => {
              searchParams.set('stage', 'Negotiation');
              setSearchParams(searchParams);
            }}
            className={`px-2.5 py-1 rounded-md border text-xs font-medium transition ${
              stageParam === 'Negotiation' ? 'bg-blue-950 text-blue-300 border-blue-800' : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
            }`}
          >
            Negotiation Stage
          </button>
        </div>
      </div>

      {/* Deals Table */}
      {loading ? (
        <TableSkeleton rows={8} />
      ) : deals.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/60 border border-slate-800 rounded-xl">
          <Briefcase className="w-10 h-10 text-slate-500 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-200">No deals match criteria</h3>
          <p className="text-xs text-slate-400 mt-1">Try clearing filters or search query.</p>
        </div>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden border border-slate-800/80">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 text-[11px]">
                <tr>
                  <th className="py-3 px-4 font-medium">Deal Code / Name</th>
                  <th className="py-3 px-4 font-medium">Account</th>
                  <th className="py-3 px-4 font-medium text-right">Value</th>
                  <th className="py-3 px-4 font-medium">Stage</th>
                  <th className="py-3 px-4 font-medium">Owner</th>
                  <th className="py-3 px-4 font-medium">
                    Risk Index
                    <InfoTooltip content="Transparent, deterministic score (0-100) computed from detected risk signals. Not a statistical loss probability." />
                  </th>
                  <th className="py-3 px-4 font-medium">
                    Data Completeness
                    <InfoTooltip content="Percentage of evaluated signals where source records were actually available. Missing tracking data is treated as Unknown, never as Risk." />
                  </th>
                  <th className="py-3 px-4 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {deals.map((deal) => (
                  <tr
                    key={deal.id}
                    onClick={() => navigate(`/deals/${deal.id}`)}
                    className="hover:bg-slate-900/60 cursor-pointer transition"
                  >
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] font-semibold text-blue-400">{deal.deal_code}</span>
                        {deal.has_manual_override && (
                          <span
                            title="This deal contains manually corrected fields with provenance tracking"
                            className="bg-purple-950 text-purple-300 border border-purple-800/60 text-[9px] px-1.5 py-0.2 rounded font-medium flex items-center gap-0.5"
                          >
                            <Edit3 className="w-2.5 h-2.5" />
                            <span>Corrected</span>
                          </span>
                        )}
                      </div>
                      <div className="text-slate-200 font-medium mt-0.5 truncate max-w-[200px]">{deal.name}</div>
                    </td>

                    <td className="py-3 px-4 font-medium text-slate-300 whitespace-nowrap">
                      {deal.account_name}
                    </td>

                    <td className="py-3 px-4 text-right font-mono font-medium text-slate-100 whitespace-nowrap">
                      ${deal.value.toLocaleString()}
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="bg-slate-900 border border-slate-700/80 text-slate-300 text-[11px] px-2 py-0.5 rounded">
                        {deal.stage}
                      </span>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap text-slate-300">
                      {deal.owner_name}
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <RiskBadge category={deal.current_risk_category || 'Low'} score={deal.current_risk_score} />
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              (deal.data_completeness_pct || 100) >= 80 ? 'bg-emerald-500' : 'bg-amber-500'
                            }`}
                            style={{ width: `${deal.data_completeness_pct || 100}%` }}
                          />
                        </div>
                        <span className="font-mono text-[11px] text-slate-400">
                          {deal.data_completeness_pct || 100}%
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button className="text-blue-400 hover:text-blue-300 font-medium inline-flex items-center gap-1">
                        <span>Inspect Cockpit</span>
                        <ChevronRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
