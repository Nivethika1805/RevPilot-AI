import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Compass, AlertCircle, ArrowRight, ShieldCheck, Play,
  CheckCircle, HelpCircle, UserCheck, RefreshCw, Plus, Edit2, Sliders
} from 'lucide-react';
import { apiClient } from '../api/client';
import { RoutingRule, Conversation } from '../types';
import { Modal } from '../components/Modal';

export const RoutingRules: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'rules' | 'review_queue' | 'dry_run'>('rules');

  // Dry run form state
  const [dryRunInput, setDryRunInput] = useState({
    topic: 'pricing',
    urgency: 'high',
    deal_stage: 'Negotiation',
    account_industry: 'Healthcare',
  });
  const [dryRunResult, setDryRunResult] = useState<any>(null);

  // Override / Assign modal
  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [selectedConversation, setSelectedConversation] = useState<Conversation | null>(null);
  const [overrideOwnerId, setOverrideOwnerId] = useState<number>(3); // Sarah Chen default
  const [overrideReason, setOverrideReason] = useState<string>('');

  // Queries
  const { data: rules = [], isLoading: rulesLoading } = useQuery({
    queryKey: ['routingRules'],
    queryFn: () => apiClient.getRoutingRules(),
  });

  const { data: reviewQueue = [], isLoading: queueLoading } = useQuery({
    queryKey: ['reviewQueue'],
    queryFn: () => apiClient.getReviewQueue(),
  });

  // Mutations
  const overrideMutation = useMutation({
    mutationFn: ({ conversationId, ownerId, reason }: { conversationId: number; ownerId: number; reason: string }) =>
      apiClient.overrideRouting(conversationId, ownerId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reviewQueue'] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setAssignModalOpen(false);
      setOverrideReason('');
      setSelectedConversation(null);
    },
  });

  const dryRunMutation = useMutation({
    mutationFn: (conditions: any) => apiClient.dryRunRouting(conditions),
    onSuccess: (data) => {
      setDryRunResult(data);
    },
  });

  const handleDryRunSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    dryRunMutation.mutate(dryRunInput);
  };

  const handleAssignSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedConversation || !overrideReason.trim()) return;
    overrideMutation.mutate({
      conversationId: selectedConversation.id,
      ownerId: overrideOwnerId,
      reason: overrideReason,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Explainable Routing</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/20 text-accent border border-accent/30">
              Deterministic Precedence
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Rules-driven assignment of sales conversations with transparent precedence, tie-break review queues, and persistent manual overrides.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border">
        <button
          onClick={() => setActiveTab('rules')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'rules'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Active Routing Rules ({rules.length})
        </button>
        <button
          onClick={() => setActiveTab('review_queue')}
          className={`px-4 py-2 text-sm font-medium border-b-2 flex items-center gap-2 transition-colors ${
            activeTab === 'review_queue'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Unassigned Review Queue
          {reviewQueue.length > 0 && (
            <span className="px-2 py-0.5 rounded-full text-xs bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30">
              {reviewQueue.length}
            </span>
          )}
        </button>
        <button
          onClick={() => setActiveTab('dry_run')}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === 'dry_run'
              ? 'border-accent text-accent'
              : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Dry-Run Simulator
        </button>
      </div>

      {/* TAB 1: RULES LIST & PRECEDENCE EXPLANATION */}
      {activeTab === 'rules' && (
        <div className="space-y-6">
          {/* Precedence Policy Callout */}
          <div className="p-4 rounded-xl border border-accent/30 bg-accent/5">
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2 mb-2">
              <Compass className="w-4 h-4 text-accent" />
              Routing Precedence Algorithm &amp; Tie-Breaking Policy
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs text-muted-foreground">
              <div className="p-2.5 rounded-lg bg-card/60 border border-border">
                <span className="font-semibold text-foreground block mb-1">1. Priority Order</span>
                Rules are evaluated in ascending order of <code className="text-accent font-mono">priority_order</code>. Lowest number wins first precedence.
              </div>
              <div className="p-2.5 rounded-lg bg-card/60 border border-border">
                <span className="font-semibold text-foreground block mb-1">2. Specificity Metric</span>
                Tied priority order resolves to the rule with higher condition count (<code className="text-accent font-mono">specificity</code>).
              </div>
              <div className="p-2.5 rounded-lg bg-card/60 border border-border">
                <span className="font-semibold text-foreground block mb-1">3. Deterministic Safety</span>
                If tied rules recommend different owners, conversation enters <strong className="text-amber-400">Review Queue</strong>. System never guesses owners.
              </div>
            </div>
          </div>

          {/* Rules Table */}
          <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    <th className="py-3 px-4 w-16">Rank</th>
                    <th className="py-3 px-4">Rule Name</th>
                    <th className="py-3 px-4">Conditions Evaluated</th>
                    <th className="py-3 px-4">Target Destination</th>
                    <th className="py-3 px-4">Specificity</th>
                    <th className="py-3 px-4">Priority Outcome</th>
                    <th className="py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border text-sm">
                  {rules.map((rule) => (
                    <tr key={rule.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-accent">
                        #{rule.priority_order}
                      </td>
                      <td className="py-3 px-4">
                        <div className="font-semibold text-foreground">{rule.name}</div>
                        <div className="text-[11px] text-muted-foreground font-mono">ID: {rule.id} • v{rule.version}</div>
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex flex-wrap gap-1 max-w-sm">
                          {Object.entries(rule.conditions || {}).map(([key, val]) => (
                            <span
                              key={key}
                              className="px-2 py-0.5 rounded text-[11px] font-mono bg-muted text-muted-foreground border border-border"
                            >
                              <strong className="text-foreground">{key}:</strong> {String(val)}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td className="py-3 px-4 text-xs font-medium text-foreground">
                        {rule.target_owner_name ? (
                          <span className="px-2 py-1 rounded bg-accent/10 border border-accent/20 text-accent">
                            User: {rule.target_owner_name}
                          </span>
                        ) : rule.target_team_name ? (
                          <span className="px-2 py-1 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400">
                            Team: {rule.target_team_name}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">Account Owner</span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-xs text-muted-foreground">
                        {rule.specificity} conditions
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-muted text-foreground border border-border">
                          {rule.priority_outcome}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${
                          rule.enabled
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : 'bg-muted text-muted-foreground'
                        }`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${rule.enabled ? 'bg-emerald-400' : 'bg-muted-foreground'}`} />
                          {rule.enabled ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: UNASSIGNED REVIEW QUEUE */}
      {activeTab === 'review_queue' && (
        <div className="space-y-4">
          <div className="p-3 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
            <span>
              Conversations in this queue were flagged by the routing engine due to ambiguous rule matches, missing account owners, or conflicting priority recommendations.
            </span>
          </div>

          <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
            {reviewQueue.length === 0 ? (
              <div className="p-12 text-center">
                <CheckCircle className="w-10 h-10 text-emerald-400 mx-auto mb-3" />
                <h3 className="text-base font-semibold text-foreground">Review Queue is Clear</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  All conversations have been deterministically assigned to a team member.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                      <th className="py-3 px-4">ID &amp; Type</th>
                      <th className="py-3 px-4">Summary</th>
                      <th className="py-3 px-4">Deal / Account</th>
                      <th className="py-3 px-4">Occurred At</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border text-sm">
                    {reviewQueue.map((conv: Conversation) => (
                      <tr key={conv.id} className="hover:bg-muted/20 transition-colors">
                        <td className="py-3 px-4">
                          <span className="font-mono text-xs text-accent font-semibold block">
                            {conv.source_record_ref || `CONV-${conv.id}`}
                          </span>
                          <span className="text-[11px] uppercase text-muted-foreground">{conv.type}</span>
                        </td>
                        <td className="py-3 px-4 max-w-md">
                          <div className="text-xs text-foreground font-medium line-clamp-2">
                            {conv.summary}
                          </div>
                          {conv.customer_intent && (
                            <div className="text-[11px] text-muted-foreground mt-0.5">
                              Intent: {conv.customer_intent}
                            </div>
                          )}
                        </td>
                        <td className="py-3 px-4 text-xs">
                          <div className="font-medium text-foreground">{conv.deal_name || `Deal #${conv.deal_id}`}</div>
                          <div className="text-muted-foreground">{conv.account_name}</div>
                        </td>
                        <td className="py-3 px-4 text-xs text-muted-foreground whitespace-nowrap">
                          {new Date(conv.occurred_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-amber-500/10 text-amber-400 border border-amber-500/20">
                            {conv.routing_status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => {
                              setSelectedConversation(conv);
                              setOverrideReason('');
                              setAssignModalOpen(true);
                            }}
                            className="btn-primary text-xs flex items-center gap-1.5 ml-auto"
                          >
                            <UserCheck className="w-3.5 h-3.5" />
                            Assign Owner
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: DRY RUN SIMULATOR */}
      {activeTab === 'dry_run' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
            <div>
              <h3 className="text-base font-bold text-foreground flex items-center gap-2">
                <Sliders className="w-4 h-4 text-accent" />
                Dry-Run Conditions
              </h3>
              <p className="text-xs text-muted-foreground mt-1">
                Simulate how the deterministic engine resolves precedence without writing any record to the database.
              </p>
            </div>

            <form onSubmit={handleDryRunSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Topic / Area
                </label>
                <select
                  value={dryRunInput.topic}
                  onChange={(e) => setDryRunInput({ ...dryRunInput, topic: e.target.value })}
                  className="w-full bg-card border border-border rounded p-2 text-xs text-foreground"
                >
                  <option value="pricing">Pricing &amp; Discounts</option>
                  <option value="renewal">Contract &amp; Renewal</option>
                  <option value="technical">Technical Architecture / Security</option>
                  <option value="implementation">Implementation &amp; Onboarding</option>
                  <option value="general">General Sales Inquiry</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Urgency Level
                </label>
                <select
                  value={dryRunInput.urgency}
                  onChange={(e) => setDryRunInput({ ...dryRunInput, urgency: e.target.value })}
                  className="w-full bg-card border border-border rounded p-2 text-xs text-foreground"
                >
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
                  Deal Stage
                </label>
                <select
                  value={dryRunInput.deal_stage}
                  onChange={(e) => setDryRunInput({ ...dryRunInput, deal_stage: e.target.value })}
                  className="w-full bg-card border border-border rounded p-2 text-xs text-foreground"
                >
                  <option value="Negotiation">Negotiation</option>
                  <option value="Proposal">Proposal</option>
                  <option value="Technical Evaluation">Technical Evaluation</option>
                  <option value="Discovery">Discovery</option>
                </select>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={dryRunMutation.isPending}
                  className="btn-primary text-xs w-full flex items-center justify-center gap-2"
                >
                  <Play className="w-3.5 h-3.5" />
                  Evaluate Precedence
                </button>
              </div>
            </form>
          </div>

          {/* Results Panel */}
          <div className="p-5 rounded-xl border border-border bg-card shadow-sm space-y-4">
            <h3 className="text-base font-bold text-foreground">Precedence Evaluation Result</h3>
            {dryRunResult ? (
              <div className="space-y-4 text-xs">
                <div className="p-3.5 rounded-lg border border-accent/30 bg-accent/10">
                  <div className="text-[10px] uppercase font-bold text-accent tracking-wider mb-1">Outcome</div>
                  <div className="text-base font-bold text-foreground">
                    Status: <span className="text-accent">{dryRunResult.status}</span>
                  </div>
                  <div className="mt-2 text-foreground font-medium">
                    Recommended Owner: <span className="font-bold text-accent">{dryRunResult.recommended_owner_name || 'None'}</span>
                  </div>
                  <div className="text-muted-foreground mt-1">
                    Reason: {dryRunResult.reason}
                  </div>
                </div>

                {dryRunResult.winning_rule && (
                  <div className="p-3 rounded-lg border border-border bg-muted/20">
                    <span className="font-semibold text-foreground block mb-1">Winning Rule:</span>
                    <div className="text-accent font-semibold">{dryRunResult.winning_rule.name}</div>
                    <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                      Priority Order: #{dryRunResult.winning_rule.priority_order} • Specificity: {dryRunResult.winning_rule.specificity}
                    </div>
                  </div>
                )}

                <div>
                  <span className="font-semibold text-foreground block mb-1.5">
                    Evaluated Rules ({dryRunResult.evaluated_rules?.length || 0}):
                  </span>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {dryRunResult.evaluated_rules?.map((r: any) => (
                      <div
                        key={r.rule_id}
                        className={`p-2 rounded border flex items-center justify-between ${
                          r.matched
                            ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                            : 'border-border bg-muted/10 text-muted-foreground'
                        }`}
                      >
                        <span className="font-medium">{r.rule_name}</span>
                        <span className="text-[10px] font-mono uppercase">
                          {r.matched ? 'Matched' : 'Conditions Not Met'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-12 text-center text-xs text-muted-foreground">
                <HelpCircle className="w-8 h-8 text-muted-foreground/40 mx-auto mb-2" />
                Select simulated conditions and click "Evaluate Precedence" to view the evaluation trace.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Manual Assignment Modal */}
      <Modal
        isOpen={assignModalOpen}
        onClose={() => setAssignModalOpen(false)}
        title="Assign Owner & Override Routing"
      >
        <form onSubmit={handleAssignSubmit} className="space-y-4">
          <div className="p-3 rounded-lg bg-accent/10 border border-accent/20 text-xs">
            <div className="font-semibold text-foreground mb-0.5">
              {selectedConversation?.summary}
            </div>
            <div className="text-muted-foreground">
              {selectedConversation?.account_name} • Ref: {selectedConversation?.source_record_ref}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
              Select Owner *
            </label>
            <select
              value={overrideOwnerId}
              onChange={(e) => setOverrideOwnerId(parseInt(e.target.value))}
              className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground"
            >
              <option value={2}>Alex Rivera (Account Executive)</option>
              <option value={3}>Sarah Chen (Pricing &amp; Commercial Lead)</option>
              <option value={4}>Marcus Brody (Renewals Manager)</option>
              <option value={5}>Dr. Elena Rostova (Solutions Architect)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">
              Override Reason (Required for Audit Trail) *
            </label>
            <textarea
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="e.g. High-value expansion requiring senior pricing desk oversight..."
              rows={3}
              required
              className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground focus:ring-1 focus:ring-accent focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setAssignModalOpen(false)}
              className="btn-secondary text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!overrideReason.trim() || overrideMutation.isPending}
              className="btn-primary text-xs"
            >
              Save Manual Override
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
