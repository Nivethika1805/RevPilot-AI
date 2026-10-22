import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, DollarSign, Calendar, Clock, AlertTriangle, ShieldAlert,
  CheckCircle2, RefreshCw, PlayCircle, Edit3, ArrowRight, CheckSquare,
  MessageSquare, User, FileText, ExternalLink, HelpCircle
} from 'lucide-react';
import { apiClient } from '../api/client';
import { Deal, RiskAssessment, RiskSignal, Activity, Conversation, Alert } from '../types';
import { RiskBadge, StatusBadge } from '../components/common/Badge';
import { InfoTooltip } from '../components/common/Tooltip';
import { Modal } from '../components/common/Modal';

export const DealDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [deal, setDeal] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Active highlighted signal
  const [selectedSignalCode, setSelectedSignalCode] = useState<string | null>(null);

  // Alert transition modal
  const [alertModalOpen, setAlertModalOpen] = useState(false);
  const [targetStatus, setTargetStatus] = useState<string>('resolved');
  const [alertNote, setAlertNote] = useState('');
  const [alertSubmitting, setAlertSubmitting] = useState(false);

  // Manual edit modal
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editName, setEditName] = useState('');
  const [editValue, setEditValue] = useState<number>(0);
  const [editStage, setEditStage] = useState('');
  const [editSubmitting, setEditSubmitting] = useState(false);

  const fetchDealDetail = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const data = await apiClient.getDealDetail(Number(id));
      setDeal(data);
      setEditName(data.name);
      setEditValue(data.value);
      setEditStage(data.stage);
    } catch (err: any) {
      setError(err?.message || 'Failed to load deal cockpit');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDealDetail();
  }, [id]);

  const handleAlertTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deal?.alerts?.[0]) return;
    setAlertSubmitting(true);
    try {
      await apiClient.transitionAlert(deal.alerts[0].id, targetStatus, alertNote);
      setAlertModalOpen(false);
      setAlertNote('');
      fetchDealDetail();
    } catch (err: any) {
      alert('Alert transition error: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setAlertSubmitting(false);
    }
  };

  const handleManualEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!deal) return;
    setEditSubmitting(true);
    try {
      await apiClient.patchDeal(deal.id, {
        name: editName,
        value: Number(editValue),
        stage: editStage
      });
      setEditModalOpen(false);
      fetchDealDetail();
    } catch (err: any) {
      alert('Failed to update deal: ' + err.message);
    } finally {
      setEditSubmitting(false);
    }
  };

  const handleCreateAction = async (title: string, priority: string) => {
    if (!deal) return;
    try {
      await apiClient.createAction({
        deal_id: deal.id,
        title,
        reason: `Generated from Deal Cockpit inspection of ${deal.name}`,
        priority
      });
      fetchDealDetail();
    } catch (err) {
      alert('Failed to create action');
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400 animate-pulse">
        Loading Deal Intelligence Cockpit...
      </div>
    );
  }

  if (error || !deal) {
    return (
      <div className="p-8 text-center bg-slate-900 border border-slate-800 rounded-xl">
        <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto mb-3" />
        <h3 className="text-sm font-semibold text-white">Deal Not Found</h3>
        <button
          onClick={() => navigate('/deals')}
          className="mt-4 px-3 py-1.5 bg-slate-800 text-xs rounded text-slate-200"
        >
          Back to Deals
        </button>
      </div>
    );
  }

  const assessment: RiskAssessment | undefined = deal.current_assessment;
  const signals = assessment?.signals || [];
  const latestAlert = deal.alerts?.[0];

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* Top Breadcrumb & Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/deals')}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold text-blue-400 bg-blue-950/60 px-2 py-0.5 rounded border border-blue-800/60">
                {deal.deal_code}
              </span>
              <h1 className="text-lg md:text-xl font-bold text-white tracking-tight">{deal.name}</h1>
              {deal.has_manual_override && (
                <span className="bg-purple-950 text-purple-300 border border-purple-800/60 text-[10px] px-2 py-0.5 rounded font-medium flex items-center gap-1">
                  <Edit3 className="w-3 h-3" />
                  <span>Manually Corrected</span>
                </span>
              )}
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              Account: <strong className="text-slate-300">{deal.account_name}</strong> • Stage: <strong className="text-slate-300">{deal.stage}</strong>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setEditModalOpen(true)}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition"
          >
            <Edit3 className="w-3.5 h-3.5 text-blue-400" />
            <span>Manual Edit</span>
          </button>
          <button
            onClick={() => navigate(`/replay?assessment_id=${assessment?.id}`)}
            className="px-3 py-1.5 rounded-lg bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 text-xs font-medium border border-blue-500/40 flex items-center gap-1.5 transition"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Replay Assessment</span>
          </button>
          <button
            onClick={() => navigate(`/replay?simulate_deal_id=${deal.id}`)}
            className="px-3.5 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold shadow-md shadow-purple-600/20 flex items-center gap-1.5 transition"
          >
            <PlayCircle className="w-4 h-4" />
            <span>Simulate a Change</span>
          </button>
        </div>
      </div>

      {/* Overview Metric Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="glass-card p-3.5 rounded-xl border border-slate-800">
          <div className="text-[11px] text-slate-400">Deal Value</div>
          <div className="text-base font-bold text-white mt-1 font-mono">${deal.value.toLocaleString()}</div>
        </div>
        <div className="glass-card p-3.5 rounded-xl border border-slate-800">
          <div className="text-[11px] text-slate-400 flex items-center gap-1">
            <span>Risk Index</span>
            <InfoTooltip content="Rule-based risk index (0-100). Not a loss probability. Indicates detected operational and commercial risk signals." />
          </div>
          <div className="mt-1">
            <RiskBadge category={deal.current_risk_category || 'Low'} score={deal.current_risk_score} size="sm" />
          </div>
        </div>
        <div className="glass-card p-3.5 rounded-xl border border-slate-800">
          <div className="text-[11px] text-slate-400 flex items-center gap-1">
            <span>Completeness</span>
            <InfoTooltip content="Evaluated knowable evidence percentage. Missing tracking records are classified as Unknown and never add risk score." />
          </div>
          <div className="text-base font-bold text-slate-200 mt-1 font-mono">{deal.data_completeness_pct}%</div>
        </div>
        <div className="glass-card p-3.5 rounded-xl border border-slate-800">
          <div className="text-[11px] text-slate-400">Owner</div>
          <div className="text-xs font-semibold text-slate-200 mt-1 truncate">{deal.owner_name}</div>
        </div>
        <div className="glass-card p-3.5 rounded-xl border border-slate-800">
          <div className="text-[11px] text-slate-400">Next Scheduled Step</div>
          <div className="text-xs font-medium text-slate-300 mt-1">
            {deal.next_activity_at ? new Date(deal.next_activity_at).toLocaleDateString() : (
              <span className="text-amber-400 font-semibold">None Scheduled</span>
            )}
          </div>
        </div>
        <div className="glass-card p-3.5 rounded-xl border border-slate-800">
          <div className="text-[11px] text-slate-400">Close Target</div>
          <div className="text-xs font-medium text-slate-300 mt-1">
            {deal.expected_close_date ? new Date(deal.expected_close_date).toLocaleDateString() : 'Unspecified'}
          </div>
        </div>
      </div>

      {/* Alert Lifecycle Control Section */}
      <div className="glass-panel p-4 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4 border border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">Manager Alert Lifecycle</h3>
            <span className="text-[10px] text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              Alert Status != Deal Risk Score
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Current Status: <strong className="text-slate-200 capitalize">{latestAlert?.status || 'Open'}</strong>
            {latestAlert?.resolution_note && (
              <span className="italic text-slate-400 ml-2">("{latestAlert.resolution_note}")</span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {latestAlert?.status !== 'resolved' ? (
            <button
              onClick={() => {
                setTargetStatus('resolved');
                setAlertModalOpen(true);
              }}
              className="px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 text-xs font-medium transition"
            >
              Resolve Alert
            </button>
          ) : (
            <button
              onClick={() => {
                setTargetStatus('reopened');
                setAlertModalOpen(true);
              }}
              className="px-3 py-1.5 rounded-lg bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/40 text-xs font-medium transition"
            >
              Reopen Alert
            </button>
          )}
        </div>
      </div>

      {/* Main Split: Risk Explanation (Left) & Evidence Panel (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Signals Breakdown (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-blue-400" />
              Risk Engine Signals & Score Contributions
            </h2>
            <span className="text-[11px] text-slate-400">Click a signal to inspect source evidence</span>
          </div>

          <div className="space-y-3">
            {signals.map((sig) => {
              const isDetected = sig.state === 'detected';
              const isUnknown = sig.state === 'unknown';
              const isSelected = selectedSignalCode === sig.signal_code;

              return (
                <div
                  key={sig.id}
                  onClick={() => setSelectedSignalCode(sig.signal_code)}
                  className={`p-4 rounded-xl border transition cursor-pointer ${
                    isSelected
                      ? 'bg-blue-950/40 border-blue-500 shadow-md shadow-blue-500/10'
                      : isDetected
                      ? 'bg-slate-900/80 border-slate-800 hover:border-slate-700'
                      : isUnknown
                      ? 'bg-slate-900/40 border-slate-800/60 opacity-75'
                      : 'bg-slate-900/30 border-slate-800/40 opacity-60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${
                        isDetected
                          ? sig.severity === 'critical'
                            ? 'bg-rose-950 text-rose-300 border-rose-800'
                            : 'bg-amber-950 text-amber-300 border-amber-800'
                          : isUnknown
                          ? 'bg-slate-800 text-slate-400 border-slate-700'
                          : 'bg-emerald-950 text-emerald-300 border-emerald-800'
                      }`}>
                        {sig.state}
                      </span>
                      <span className="text-xs font-bold text-white">{sig.signal_code.replace(/_/g, ' ')}</span>
                    </div>

                    <div className="text-right shrink-0">
                      <span className={`text-xs font-mono font-bold ${isDetected ? 'text-rose-400' : 'text-slate-400'}`}>
                        +{sig.score_contribution} pts
                      </span>
                    </div>
                  </div>

                  <p className="text-xs text-slate-300 mt-2 leading-relaxed">{sig.explanation}</p>
                  <p className="text-[11px] text-slate-400 mt-1 italic">
                    <strong className="text-slate-400 font-medium">Why it matters: </strong>{sig.why_it_matters}
                  </p>

                  {/* Evidence Chips */}
                  {sig.evidence_ids && sig.evidence_ids.length > 0 && (
                    <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex flex-wrap gap-1.5">
                      {sig.evidence_ids.map((ev, i) => (
                        <span
                          key={i}
                          className="font-mono text-[10px] text-blue-300 bg-blue-950/80 border border-blue-800/60 px-2 py-0.5 rounded"
                        >
                          {ev.source_ref || 'Evidence'}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Source Evidence Panel & Recommended Actions (5 Cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Recommended Next Actions */}
          <div className="glass-panel p-5 rounded-xl space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center justify-between">
              <span>Recommended Follow-ups</span>
              <span className="text-[10px] text-emerald-400">1-Click Dispatch</span>
            </h3>

            <div className="space-y-2">
              <button
                onClick={() => handleCreateAction(`Review Pricing Proposal & Commercials for ${deal.name}`, 'critical')}
                className="w-full text-left p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-200 flex items-center justify-between transition"
              >
                <span>Review Pricing Proposal & Commercials</span>
                <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
              </button>
              <button
                onClick={() => handleCreateAction(`Schedule Customer Follow-up & Re-engagement for ${deal.name}`, 'high')}
                className="w-full text-left p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-200 flex items-center justify-between transition"
              >
                <span>Schedule Customer Follow-up</span>
                <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
              </button>
              <button
                onClick={() => handleCreateAction(`Confirm Technical Requirements & Security Baseline for ${deal.name}`, 'high')}
                className="w-full text-left p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-200 flex items-center justify-between transition"
              >
                <span>Confirm Technical Requirements</span>
                <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
              </button>
              <button
                onClick={() => handleCreateAction(`Escalate Approaching Deadline with Executive Sponsor on ${deal.name}`, 'critical')}
                className="w-full text-left p-2.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-800 text-xs text-slate-200 flex items-center justify-between transition"
              >
                <span>Escalate Approaching Deadline</span>
                <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
              </button>
            </div>
          </div>

          {/* Source Evidence Panel */}
          <div className="glass-panel p-5 rounded-xl space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300">
              Source Evidence Audit Trail
            </h3>

            <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
              {deal.recent_conversations?.map((c: Conversation) => (
                <div key={c.id} className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] text-blue-400 font-bold">{c.source_record_ref}</span>
                    <span className="text-[10px] text-slate-400">{new Date(c.occurred_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed text-[11px]">{c.summary}</p>
                  {c.sentiment_basis && (
                    <div className="text-[10px] text-slate-400 italic bg-slate-900 p-1.5 rounded">
                      Basis: "{c.sentiment_basis}"
                    </div>
                  )}
                </div>
              ))}

              {deal.recent_activities?.map((a: Activity) => (
                <div key={a.id} className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] text-purple-400">{a.source_ref}</span>
                    <span className="text-[10px] text-slate-400">{new Date(a.occurred_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-slate-300 text-[11px]">{a.detail}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Field Provenance Table (Manual Corrections vs Source Baseline) */}
      <div className="glass-panel p-5 rounded-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
              <FileText className="w-4 h-4 text-purple-400" />
              Field-Level Provenance & Manual Correction Log
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Tracks source value baseline vs manual corrections to ensure external imports never overwrite human decisions silently.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 text-[11px]">
              <tr>
                <th className="py-2.5 px-3 font-medium">Field Name</th>
                <th className="py-2.5 px-3 font-medium">Source Baseline (Last Import)</th>
                <th className="py-2.5 px-3 font-medium">Current Active Value</th>
                <th className="py-2.5 px-3 font-medium">Overridden?</th>
                <th className="py-2.5 px-3 font-medium">Last Update Source</th>
                <th className="py-2.5 px-3 font-medium text-right">Updated At</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
              {deal.field_provenances?.map((p: any) => (
                <tr key={p.field_name} className="hover:bg-slate-900/40">
                  <td className="py-2 px-3 text-slate-200 font-semibold">{p.field_name}</td>
                  <td className="py-2 px-3 text-slate-400">{p.source_value || 'None'}</td>
                  <td className="py-2 px-3 text-white font-medium">{p.current_value || 'None'}</td>
                  <td className="py-2 px-3">
                    {p.is_overridden ? (
                      <span className="text-purple-400 bg-purple-950/80 px-2 py-0.5 rounded border border-purple-800 text-[10px]">
                        Manual Override
                      </span>
                    ) : (
                      <span className="text-slate-400">Source Baseline</span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-slate-300 capitalize">{p.last_update_source}</td>
                  <td className="py-2 px-3 text-right text-slate-400">{new Date(p.updated_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Alert State Transition Modal */}
      <Modal
        isOpen={alertModalOpen}
        onClose={() => setAlertModalOpen(false)}
        title="Transition Alert Lifecycle"
      >
        <form onSubmit={handleAlertTransition} className="space-y-4 text-xs">
          <div className="bg-blue-950/40 p-3 rounded-lg border border-blue-900/60 text-blue-200 text-[11px] leading-relaxed">
            <strong>Important: </strong>Transitioning or resolving an alert updates management lifecycle tracking, but does <em>not</em> alter the deal's objective risk score.
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1">Target Status</label>
            <input
              type="text"
              readOnly
              value={targetStatus.toUpperCase()}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-300 font-mono text-xs"
            />
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1">Audit Resolution Note (Required)</label>
            <textarea
              required
              rows={3}
              value={alertNote}
              onChange={(e) => setAlertNote(e.target.value)}
              placeholder="Document the resolution reason or context for audit trail..."
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setAlertModalOpen(false)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={alertSubmitting}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-50"
            >
              {alertSubmitting ? 'Updating...' : 'Confirm Transition'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Manual Edit Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Manual Correction (Provenance Tracked)"
      >
        <form onSubmit={handleManualEdit} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 font-medium mb-1">Deal Name</label>
            <input
              type="text"
              required
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1">Deal Value ($)</label>
            <input
              type="number"
              required
              value={editValue}
              onChange={(e) => setEditValue(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
            />
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1">Stage</label>
            <select
              value={editStage}
              onChange={(e) => setEditStage(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
            >
              <option value="Discovery">Discovery</option>
              <option value="Proposal">Proposal</option>
              <option value="Negotiation">Negotiation</option>
              <option value="Legal/Review">Legal/Review</option>
              <option value="Closed">Closed</option>
            </select>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setEditModalOpen(false)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={editSubmitting}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-50"
            >
              {editSubmitting ? 'Saving...' : 'Save Manual Edit'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
