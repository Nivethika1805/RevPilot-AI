import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings as SettingsIcon, Sliders, Shield, RefreshCw,
  Info, Cpu, Database, Check, Clock, AlertTriangle
} from 'lucide-react';
import { apiClient } from '../api/client';
import { Modal } from '../components/Modal';

export const Settings: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedSignal, setSelectedSignal] = useState<any>(null);
  const [editWeight, setEditWeight] = useState<number>(20);
  const [editModalOpen, setEditModalOpen] = useState(false);

  const { data: settingsData, isLoading } = useQuery({
    queryKey: ['systemSettings'],
    queryFn: () => apiClient.getSettings(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ code, payload }: { code: string; payload: any }) =>
      apiClient.updateRiskConfig(code, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['systemSettings'] });
      setEditModalOpen(false);
    },
  });

  const recomputeMutation = useMutation({
    mutationFn: () => apiClient.recomputeRisk(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deals'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings &amp; Model Governance</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/20 text-accent border border-accent/30">
              System Configuration
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Configure risk index signal weights, inspect model versioning, review pinned time horizons, and trigger system re-evaluations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => recomputeMutation.mutate()}
            disabled={recomputeMutation.isPending}
            className="btn-primary text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${recomputeMutation.isPending ? 'animate-spin' : ''}`} />
            {recomputeMutation.isPending ? 'Recomputing Pipeline...' : 'Recompute All Deals'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Risk Signal Weights Table */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-foreground flex items-center gap-2">
              <Sliders className="w-4 h-4 text-accent" />
              Risk Index Signal Weights (Versioned)
            </h3>
            <span className="text-xs font-mono text-muted-foreground">
              Snapshot v{settingsData?.risk_configs?.[0]?.version || 1}
            </span>
          </div>

          <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    <th className="py-3 px-4">Signal Code</th>
                    <th className="py-3 px-4">Weight Applied</th>
                    <th className="py-3 px-4">Thresholds</th>
                    <th className="py-3 px-4">State</th>
                    <th className="py-3 px-4 text-right">Edit</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(settingsData?.risk_configs || []).map((cfg: any) => (
                    <tr key={cfg.signal_code} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-foreground">
                        {cfg.signal_code}
                      </td>
                      <td className="py-3 px-4 font-bold text-accent">
                        {cfg.weight} pts
                      </td>
                      <td className="py-3 px-4 font-mono text-muted-foreground text-[11px]">
                        {JSON.stringify(cfg.threshold_params || {})}
                      </td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          cfg.enabled
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-muted text-muted-foreground'
                        }`}>
                          {cfg.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => {
                            setSelectedSignal(cfg);
                            setEditWeight(cfg.weight);
                            setEditModalOpen(true);
                          }}
                          className="btn-secondary text-[11px] py-1 px-2.5"
                        >
                          Modify
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* System Horizon & Runtime Info */}
        <div className="space-y-4">
          <h3 className="text-base font-bold text-foreground flex items-center gap-2">
            <Info className="w-4 h-4 text-accent" />
            Environment &amp; Horizon
          </h3>

          <div className="p-4 rounded-xl border border-border bg-card shadow-sm space-y-3 text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-accent" /> As-Of Anchor Date
              </span>
              <span className="font-mono font-bold text-foreground">
                {settingsData?.as_of_date || '2026-10-20'}
              </span>
            </div>

            <div className="flex items-center justify-between pb-2 border-b border-border">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-emerald-400" /> Public Demo Mode
              </span>
              <span className="font-semibold text-emerald-400">
                ACTIVE (demo_evaluator)
              </span>
            </div>

            <div className="flex items-center justify-between pb-2 border-b border-border">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Cpu className="w-3.5 h-3.5 text-accent" /> Extraction Engine
              </span>
              <span className="font-semibold text-foreground">
                Deterministic Regex Spans
              </span>
            </div>

            <div className="flex items-center justify-between">
              <span className="text-muted-foreground flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-accent" /> Database Dialect
              </span>
              <span className="font-mono text-foreground">
                SQLite 3 (WAL mode)
              </span>
            </div>
          </div>

          {/* Transparent methodology note */}
          <div className="p-4 rounded-xl border border-accent/20 bg-accent/5 text-xs text-muted-foreground space-y-2">
            <div className="font-semibold text-foreground flex items-center gap-1.5">
              <Info className="w-4 h-4 text-accent" /> Risk Methodology Governance
            </div>
            <p>
              RevPilot AI calculates a <strong>Rule-based risk index (0–100)</strong> based strictly on verified evidence. It is never presented as an actuarial loss probability.
            </p>
            <p>
              Missing evidence is categorized as <code>unknown</code> (adding 0 points), reducing the Data Completeness metric rather than penalizing the opportunity score.
            </p>
          </div>
        </div>
      </div>

      {/* Edit Signal Weight Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title={`Adjust Signal Weight: ${selectedSignal?.signal_code}`}
      >
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            Updating signal weights increments the rules version and generates an immutable audit event.
          </p>

          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
              Weight (Points 0–50)
            </label>
            <input
              type="number"
              min={0}
              max={50}
              value={editWeight}
              onChange={(e) => setEditWeight(parseInt(e.target.value) || 0)}
              className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground focus:ring-1 focus:ring-accent focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={() => setEditModalOpen(false)} className="btn-secondary text-xs">
              Cancel
            </button>
            <button
              onClick={() => {
                if (!selectedSignal) return;
                updateMutation.mutate({
                  code: selectedSignal.signal_code,
                  payload: { weight: editWeight },
                });
              }}
              disabled={updateMutation.isPending}
              className="btn-primary text-xs"
            >
              Save New Weight
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
