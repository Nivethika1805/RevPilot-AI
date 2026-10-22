import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  RotateCcw, Sliders, CheckCircle2, AlertTriangle, ShieldCheck,
  TrendingDown, ArrowRight, Play, Database, FileText, Check, HelpCircle
} from 'lucide-react';
import { apiClient } from '../api/client';
import { RiskBadge } from '../components/Badge';
import { Modal } from '../components/Modal';

export const DecisionReplay: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'replay' | 'simulate'>('replay');

  // Replay state
  const [assessmentIdInput, setAssessmentIdInput] = useState<number>(1);
  const [replayTargetId, setReplayTargetId] = useState<number>(1);

  // Simulator state
  const [simDealId, setSimDealId] = useState<number>(1);
  const [simChanges, setSimChanges] = useState({
    simulate_customer_reply: true,
    simulate_pricing_resolved: true,
    simulate_next_step: true,
  });
  const [simCommitModalOpen, setSimCommitModalOpen] = useState(false);
  const [simCommitNote, setSimCommitNote] = useState('Executive discount and next call scheduled');

  // Queries
  const { data: replayData, isLoading: replayLoading, refetch: refetchReplay } = useQuery({
    queryKey: ['riskReplay', replayTargetId],
    queryFn: () => apiClient.replayAssessment(replayTargetId),
    enabled: !!replayTargetId,
  });

  // Simulator mutation (pure in-memory dry-run)
  const simMutation = useMutation({
    mutationFn: () => apiClient.simulateRisk(simDealId, simChanges),
  });

  // Simulator commit mutation
  const commitMutation = useMutation({
    mutationFn: () => apiClient.commitSimulation(simDealId, simChanges, simCommitNote),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
      setSimCommitModalOpen(false);
    },
  });

  const handleRunReplay = (e: React.FormEvent) => {
    e.preventDefault();
    setReplayTargetId(assessmentIdInput);
  };

  const handleRunSimulation = (e: React.FormEvent) => {
    e.preventDefault();
    simMutation.mutate();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Decision Replay &amp; What-If Simulator</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/20 text-accent border border-accent/30">
              Deterministic Verification
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Audit cryptographic assessment snapshots and test hypothetical sales actions without mutating live pipeline data.
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-border">
        <button
          onClick={() => setActiveTab('replay')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'replay'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <RotateCcw className="w-4 h-4" />
          Decision Replay
        </button>
        <button
          onClick={() => setActiveTab('simulate')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === 'simulate'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          <Sliders className="w-4 h-4" />
          What-If Simulator
        </button>
      </div>

      {/* TAB 1: DECISION REPLAY */}
      {activeTab === 'replay' && (
        <div className="space-y-6">
          {/* Query Bar */}
          <form onSubmit={handleRunReplay} className="p-4 rounded-xl border border-border bg-card shadow-sm flex items-center gap-4 text-xs">
            <span className="font-semibold uppercase text-muted-foreground">Select Assessment ID:</span>
            <input
              type="number"
              value={assessmentIdInput}
              onChange={(e) => setAssessmentIdInput(parseInt(e.target.value) || 1)}
              className="bg-card border border-border rounded px-3 py-1.5 text-foreground w-24"
            />
            <button type="submit" className="btn-primary text-xs flex items-center gap-1.5">
              <RotateCcw className="w-3.5 h-3.5" />
              Replay Engine Execution
            </button>
          </form>

          {replayLoading ? (
            <div className="p-12 text-center text-sm text-muted-foreground">
              Re-executing pure risk engine against snapshot...
            </div>
          ) : replayData ? (
            <div className="space-y-6">
              {/* Verification Badge Banner */}
              {(() => {
                const isMatch = Boolean(replayData.matches_stored ?? replayData.replay_matches_stored_result);
                return (
                  <div className={`p-4 rounded-xl border flex items-center justify-between ${
                    isMatch
                      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                      : 'border-rose-500/30 bg-rose-500/10 text-rose-300'
                  }`}>
                    <div className="flex items-center gap-3">
                      {isMatch ? (
                        <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
                      ) : (
                        <AlertTriangle className="w-6 h-6 text-rose-400 shrink-0" />
                      )}
                      <div>
                        <div className="text-sm font-bold text-foreground">
                          Deterministic Reproducibility: {isMatch ? 'VERIFIED MATCH' : 'SCORE MISMATCH DETECTED'}
                        </div>
                        <div className="text-xs text-muted-foreground mt-0.5">
                          {isMatch ? (
                            `Recomputed score (${replayData.recomputed_score}) exactly matches stored database score (${replayData.stored_score}) using rules version v${replayData.stored_rules_version || 1}.`
                          ) : (
                            `Recomputed score (${replayData.recomputed_score}) differs from stored database score (${replayData.stored_score}) by ${Math.abs(Number(replayData.recomputed_score) - Number(replayData.stored_score)).toFixed(1)} pts. Audit snapshot mismatch.`
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="text-right font-mono text-xs">
                      Snapshot: v{replayData.stored_rules_version || 1} • Stored: {replayData.stored_score}/100 • Recomputed: {replayData.recomputed_score}/100
                    </div>
                  </div>
                );
              })()}

              {/* Signals Comparison Table */}
              <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
                <div className="p-3 bg-muted/40 font-semibold text-xs text-muted-foreground border-b border-border">
                  Signals Evaluated in Replay
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-border text-[11px] font-semibold text-muted-foreground uppercase">
                        <th className="py-2.5 px-4">Signal Code</th>
                        <th className="py-2.5 px-4">State</th>
                        <th className="py-2.5 px-4">Severity</th>
                        <th className="py-2.5 px-4">Weight Applied</th>
                        <th className="py-2.5 px-4">Score Contribution</th>
                        <th className="py-2.5 px-4">Explanation</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {(replayData.signals || []).map((sig: any) => (
                        <tr key={sig.signal_code} className="hover:bg-muted/10">
                          <td className="py-2.5 px-4 font-mono font-medium text-foreground">{sig.signal_code}</td>
                          <td className="py-2.5 px-4">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              sig.state === 'detected' ? 'bg-rose-500/20 text-rose-300' :
                              sig.state === 'unknown' ? 'bg-amber-500/20 text-amber-300' :
                              'bg-muted text-muted-foreground'
                            }`}>
                              {sig.state}
                            </span>
                          </td>
                          <td className="py-2.5 px-4 uppercase text-[10px] font-semibold">{sig.severity}</td>
                          <td className="py-2.5 px-4 font-mono">{sig.weight_applied} pts</td>
                          <td className="py-2.5 px-4 font-mono font-bold text-accent">+{sig.score_contribution} pts</td>
                          <td className="py-2.5 px-4 text-muted-foreground max-w-sm">{sig.explanation}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Inputs Considered */}
              <div className="p-4 rounded-xl border border-border bg-card text-xs space-y-3">
                <div className="font-bold text-foreground flex items-center gap-2">
                  <Database className="w-4 h-4 text-accent" />
                  Source Evidence Considered in Snapshot
                </div>
                <div className="flex flex-wrap gap-2">
                  {(replayData.inputs_considered?.evidence_refs || []).map((ref: string, idx: number) => (
                    <span key={idx} className="px-2 py-1 rounded bg-muted/60 border border-border font-mono text-[11px] text-accent">
                      {ref}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}

      {/* TAB 2: WHAT-IF SIMULATOR */}
      {activeTab === 'simulate' && (
        <div className="space-y-6">
          {/* Prominent Warning Callout */}
          <div className="p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 text-xs text-amber-300 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-bold text-amber-200 uppercase tracking-wider mb-1">
                Hypothetical Simulation Mode — Zero In-Database Mutation
              </div>
              Running this simulation calculates outcomes purely in memory. Live deal records, activity logs, alerts, and audit history remain untouched until you explicitly click "Commit Changes".
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Input Controls */}
            <form onSubmit={handleRunSimulation} className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Sliders className="w-4 h-4 text-accent" />
                Simulated Sales Actions
              </h3>

              <div>
                <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Target Deal ID
                </label>
                <input
                  type="number"
                  value={simDealId}
                  onChange={(e) => setSimDealId(parseInt(e.target.value) || 1)}
                  className="w-full bg-card border border-border rounded p-2 text-xs text-foreground"
                />
              </div>

              <div className="space-y-3 pt-2">
                <label className="flex items-center gap-3 p-3 rounded-lg border border-border bg-muted/10 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={simChanges.simulate_customer_reply}
                    onChange={(e) => setSimChanges({ ...simChanges, simulate_customer_reply: e.target.checked })}
                    className="rounded text-accent focus:ring-accent"
                  />
                  <div className="text-xs">
                    <span className="font-semibold text-foreground block">Customer replied today</span>
                    <span className="text-muted-foreground">Clears NO_RECENT_CUSTOMER_RESPONSE signal.</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 rounded-lg border border-border bg-muted/10 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={simChanges.simulate_pricing_resolved}
                    onChange={(e) => setSimChanges({ ...simChanges, simulate_pricing_resolved: e.target.checked })}
                    className="rounded text-accent focus:ring-accent"
                  />
                  <div className="text-xs">
                    <span className="font-semibold text-foreground block">Resolve pricing objection</span>
                    <span className="text-muted-foreground">Simulates executive commercial agreement.</span>
                  </div>
                </label>

                <label className="flex items-center gap-3 p-3 rounded-lg border border-border bg-muted/10 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={simChanges.simulate_next_step}
                    onChange={(e) => setSimChanges({ ...simChanges, simulate_next_step: e.target.checked })}
                    className="rounded text-accent focus:ring-accent"
                  />
                  <div className="text-xs">
                    <span className="font-semibold text-foreground block">Schedule next step demo</span>
                    <span className="text-muted-foreground">Sets next_activity_at within 7 days.</span>
                  </div>
                </label>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={simMutation.isPending}
                  className="btn-primary text-xs w-full flex items-center justify-center gap-2"
                >
                  <Play className="w-3.5 h-3.5" />
                  {simMutation.isPending ? 'Simulating...' : 'Run Simulation'}
                </button>
              </div>
            </form>

            {/* Results Panel */}
            <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
              <h3 className="text-base font-bold text-foreground">Projected Risk Impact</h3>

              {simMutation.data ? (
                <div className="space-y-4 text-xs">
                  {/* Before vs After Comparison Card */}
                  <div className="grid grid-cols-2 gap-3 p-3.5 rounded-lg border border-border bg-muted/20">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-muted-foreground block mb-1">
                        Current Baseline
                      </span>
                      <div className="text-2xl font-bold text-foreground">
                        {simMutation.data.before_score}
                        <span className="text-xs text-muted-foreground font-normal"> / 100</span>
                      </div>
                      <div className="mt-1">
                        <RiskBadge category={simMutation.data.before_category} />
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] uppercase font-bold text-accent block mb-1">
                        Simulated Outcome
                      </span>
                      <div className="text-2xl font-bold text-emerald-400">
                        {simMutation.data.after_score}
                        <span className="text-xs text-muted-foreground font-normal"> / 100</span>
                      </div>
                      <div className="mt-1">
                        <RiskBadge category={simMutation.data.after_category} />
                      </div>
                    </div>
                  </div>

                  {/* Score Delta */}
                  <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 flex items-center justify-between">
                    <span className="font-semibold flex items-center gap-1.5">
                      <TrendingDown className="w-4 h-4" />
                      Risk Index Reduction:
                    </span>
                    <span className="font-mono font-bold text-sm">
                      -{simMutation.data.score_reduction} pts
                    </span>
                  </div>

                  {/* Removed Signals */}
                  <div>
                    <span className="font-semibold text-foreground block mb-1">
                      Signals Extinguished ({simMutation.data.signals_removed?.length || 0}):
                    </span>
                    <div className="space-y-1">
                      {(simMutation.data.signals_removed || []).map((code: string) => (
                        <div key={code} className="p-1.5 rounded bg-card border border-border font-mono text-[11px] text-emerald-400">
                          ✓ {code}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Commit Button */}
                  <div className="pt-2">
                    <button
                      onClick={() => setSimCommitModalOpen(true)}
                      className="btn-primary text-xs w-full flex items-center justify-center gap-2"
                    >
                      <Database className="w-3.5 h-3.5" />
                      Commit These Changes to Real Records
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-12 text-center text-xs text-muted-foreground">
                  <HelpCircle className="w-8 h-8 text-muted-foreground/40 mx-auto mb-2" />
                  Select hypothetical conditions and click "Run Simulation" to preview the impact.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Commit Simulation Modal */}
      <Modal
        isOpen={simCommitModalOpen}
        onClose={() => setSimCommitModalOpen(false)}
        title="Commit Simulation to Real Records"
      >
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            This operation will create real sales activity, resolve selected findings, and recalculate the live deal risk score in the database.
          </p>

          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
              Audit Note (Required) *
            </label>
            <textarea
              value={simCommitNote}
              onChange={(e) => setSimCommitNote(e.target.value)}
              rows={3}
              className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground focus:ring-1 focus:ring-accent focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={() => setSimCommitModalOpen(false)} className="btn-secondary text-xs">
              Cancel
            </button>
            <button
              onClick={() => commitMutation.mutate()}
              disabled={commitMutation.isPending || !simCommitNote.trim()}
              className="btn-primary text-xs"
            >
              {commitMutation.isPending ? 'Committing...' : 'Confirm Real Commit'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
