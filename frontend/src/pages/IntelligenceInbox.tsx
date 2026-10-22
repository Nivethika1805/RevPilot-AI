import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Search, Filter, MessageSquare, Phone, Mail, FileText, ChevronRight,
  X, AlertTriangle, ShieldAlert, CheckCircle2, UserCheck, ArrowRight, User
} from 'lucide-react';
import { apiClient } from '../api/client';
import { Conversation, Finding, EvidenceExcerpt } from '../types';
import { StatusBadge, RiskBadge } from '../components/common/Badge';
import { TableSkeleton } from '../components/common/Skeleton';
import { Modal } from '../components/common/Modal';

export const IntelligenceInbox: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [selectedConv, setSelectedConv] = useState<Conversation | null>(null);
  const [drawerLoading, setDrawerLoading] = useState(false);

  // Filters from query params
  const qParam = searchParams.get('q') || '';
  const typeParam = searchParams.get('type') || '';
  const urgencyParam = searchParams.get('urgency') || '';
  const routingStatusParam = searchParams.get('routing_status') || '';
  const unassignedParam = searchParams.get('unassigned') === 'true';

  // Override modal state
  const [overrideModalOpen, setOverrideModalOpen] = useState(false);
  const [overrideOwnerId, setOverrideOwnerId] = useState<number>(2);
  const [overrideReason, setOverrideReason] = useState('');
  const [overrideSubmitting, setOverrideSubmitting] = useState(false);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const res = await apiClient.getConversations({
        q: qParam || undefined,
        type: typeParam || undefined,
        urgency: urgencyParam || undefined,
        routing_status: routingStatusParam || undefined,
        unassigned: unassignedParam || undefined,
        limit: 30,
      });
      setConversations(res.items);
      setTotal(res.total);
    } catch (err) {
      console.error('Failed to load conversations', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [qParam, typeParam, urgencyParam, routingStatusParam, unassignedParam]);

  const openDrawer = async (conv: Conversation) => {
    setSelectedConv(conv);
    setDrawerLoading(true);
    try {
      const full = await apiClient.getConversationDetail(conv.id);
      setSelectedConv(full);
    } catch (err) {
      console.error('Failed to load conversation details', err);
    } finally {
      setDrawerLoading(false);
    }
  };

  const handleOverrideSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedConv) return;
    setOverrideSubmitting(true);
    try {
      await apiClient.overrideRouting(selectedConv.id, overrideOwnerId, overrideReason || 'Manual manager reassignment');
      setOverrideModalOpen(false);
      setOverrideReason('');
      // Refresh details
      const updated = await apiClient.getConversationDetail(selectedConv.id);
      setSelectedConv(updated);
      fetchConversations();
    } catch (err) {
      alert('Failed to override routing: ' + err);
    } finally {
      setOverrideSubmitting(false);
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case 'call': return <Phone className="w-3.5 h-3.5 text-blue-400" />;
      case 'meeting': return <MessageSquare className="w-3.5 h-3.5 text-purple-400" />;
      case 'email': return <Mail className="w-3.5 h-3.5 text-emerald-400" />;
      default: return <FileText className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header & Filter Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            Intelligence Inbox
            <span className="text-xs font-normal text-slate-400 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
              {total} Total Conversations
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Search transcripts, review extracted objections, inspect source evidence, and manage routing.
          </p>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <button
            onClick={() => {
              searchParams.delete('urgency');
              searchParams.delete('unassigned');
              searchParams.delete('type');
              setSearchParams(searchParams);
            }}
            className={`px-2.5 py-1 rounded-md border text-xs font-medium transition ${
              !urgencyParam && !unassignedParam ? 'bg-blue-600 text-white border-blue-500' : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
            }`}
          >
            All
          </button>
          <button
            onClick={() => {
              searchParams.set('unassigned', 'true');
              setSearchParams(searchParams);
            }}
            className={`px-2.5 py-1 rounded-md border text-xs font-medium transition ${
              unassignedParam ? 'bg-rose-950 text-rose-300 border-rose-800' : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
            }`}
          >
            Unassigned Review Queue
          </button>
          <button
            onClick={() => {
              searchParams.set('urgency', 'critical');
              setSearchParams(searchParams);
            }}
            className={`px-2.5 py-1 rounded-md border text-xs font-medium transition ${
              urgencyParam === 'critical' ? 'bg-rose-950 text-rose-300 border-rose-800' : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
            }`}
          >
            Critical Urgency
          </button>
        </div>
      </div>

      {/* Conversations List Table */}
      {loading ? (
        <TableSkeleton rows={8} />
      ) : conversations.length === 0 ? (
        <div className="p-12 text-center bg-slate-900/60 border border-slate-800 rounded-xl">
          <MessageSquare className="w-10 h-10 text-slate-500 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-200">No conversations found</h3>
          <p className="text-xs text-slate-400 mt-1">Adjust search parameters or clear active filters.</p>
        </div>
      ) : (
        <div className="glass-panel rounded-xl overflow-hidden border border-slate-800/80">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 text-[11px]">
                <tr>
                  <th className="py-3 px-4 font-medium">Ref / Type</th>
                  <th className="py-3 px-4 font-medium">Account & Deal</th>
                  <th className="py-3 px-4 font-medium">Summary & Extracted Intent</th>
                  <th className="py-3 px-4 font-medium">Urgency</th>
                  <th className="py-3 px-4 font-medium">Routing Status</th>
                  <th className="py-3 px-4 font-medium">Assigned Owner</th>
                  <th className="py-3 px-4 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {conversations.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => openDrawer(c)}
                    className="hover:bg-slate-900/60 cursor-pointer transition"
                  >
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {getTypeIcon(c.type)}
                        <span className="font-mono text-slate-300 text-[11px] font-medium">{c.source_record_ref}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{new Date(c.occurred_at).toLocaleDateString()}</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-medium text-slate-200">{c.account_name}</div>
                      <div className="text-[11px] text-slate-400 truncate max-w-[180px]">{c.deal_name}</div>
                    </td>

                    <td className="py-3 px-4">
                      <div className="text-slate-200 line-clamp-1 max-w-md">{c.summary}</div>
                      {c.sentiment_label && (
                        <div className="text-[10px] text-slate-400 mt-0.5 flex items-center gap-1.5">
                          <span className="capitalize">Sentiment: {c.sentiment_label}</span>
                          {c.customer_intent && (
                            <>
                              <span>•</span>
                              <span className="truncate max-w-[200px]">{c.customer_intent}</span>
                            </>
                          )}
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded border ${
                        c.urgency === 'critical'
                          ? 'bg-rose-950 text-rose-300 border-rose-800'
                          : c.urgency === 'high'
                          ? 'bg-amber-950 text-amber-300 border-amber-800'
                          : 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}>
                        {c.urgency}
                      </span>
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap">
                      <StatusBadge status={c.routing_status} />
                    </td>

                    <td className="py-3 px-4 whitespace-nowrap text-slate-300">
                      {c.assigned_user_name || <span className="text-rose-400 italic font-medium">Unassigned</span>}
                    </td>

                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button className="text-blue-400 hover:text-blue-300 p-1">
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

      {/* Conversation Detail Drawer */}
      {selectedConv && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col animate-slideLeft">
          {/* Drawer Header */}
          <div className="h-16 px-6 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-900/90 backdrop-blur">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-blue-400 bg-blue-950/60 px-2.5 py-1 rounded border border-blue-800/60">
                {selectedConv.source_record_ref}
              </span>
              <span className="text-xs text-slate-400 capitalize">• {selectedConv.type}</span>
            </div>
            <button
              onClick={() => setSelectedConv(null)}
              className="p-1 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Overview Card */}
            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-base font-bold text-white">{selectedConv.account_name}</h3>
                  <div className="text-xs text-blue-400 hover:underline cursor-pointer mt-0.5" onClick={() => navigate(`/deals/${selectedConv.deal_id}`)}>
                    {selectedConv.deal_name} (Click to inspect deal cockpit)
                  </div>
                </div>
                <StatusBadge status={selectedConv.routing_status} />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs pt-2 border-t border-slate-800/80">
                <div>
                  <span className="text-slate-400 text-[11px]">Assigned Rep:</span>
                  <div className="font-medium text-slate-200 mt-0.5">
                    {selectedConv.assigned_user_name || 'Unassigned'}
                  </div>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Occurred:</span>
                  <div className="font-medium text-slate-200 mt-0.5">
                    {new Date(selectedConv.occurred_at).toLocaleDateString()}
                  </div>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px]">Urgency:</span>
                  <div className="font-medium capitalize text-slate-200 mt-0.5">{selectedConv.urgency}</div>
                </div>
              </div>
            </div>

            {/* Summary & Sentiment Basis */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Discussion Summary & Sentiment</h4>
              <div className="bg-slate-950/40 p-4 rounded-xl border border-slate-800/80 space-y-2">
                <p className="text-xs text-slate-200 leading-relaxed">{selectedConv.summary}</p>
                {selectedConv.sentiment_basis && (
                  <div className="text-xs bg-slate-900/80 p-2.5 rounded border border-slate-800 text-slate-300">
                    <strong className="text-slate-400 font-medium">Sentiment Basis: </strong>
                    <span className="italic">"{selectedConv.sentiment_basis}"</span>
                  </div>
                )}
              </div>
            </div>

            {/* Extracted Findings & Evidence */}
            {selectedConv.findings && selectedConv.findings.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                  <span>Extracted Findings & Offsets</span>
                  <span className="text-[10px] text-blue-400 font-mono">Rule-extracted (Deterministic)</span>
                </h4>
                <div className="space-y-2">
                  {selectedConv.findings.map((f) => (
                    <div key={f.id} className="bg-slate-950/50 p-3 rounded-lg border border-slate-800 text-xs space-y-1">
                      <div className="flex items-center justify-between font-medium">
                        <span className="text-amber-300">{f.label}</span>
                        <span className="font-mono text-[10px] text-slate-400">{f.evidence?.source_ref}</span>
                      </div>
                      {f.evidence && (
                        <p className="text-slate-300 text-[11px] bg-slate-900/80 p-2 rounded border border-slate-800/60 font-mono">
                          "{f.evidence.excerpt_text}"
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Routing Decision & Precedence Rationale */}
            {selectedConv.routing_decision && (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Explainable Routing Decision</h4>
                  <button
                    onClick={() => setOverrideModalOpen(true)}
                    className="text-xs text-blue-400 hover:text-blue-300 font-medium transition"
                  >
                    Manual Override
                  </button>
                </div>
                <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Winning Rule:</span>
                    <span className="font-medium text-slate-200">{selectedConv.routing_decision.winning_rule}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Assigned Candidate:</span>
                    <span className="font-medium text-emerald-400">{selectedConv.routing_decision.recommended_owner}</span>
                  </div>
                  {selectedConv.routing_decision.alternative_owner && (
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Rejected Alternative:</span>
                      <span className="font-medium text-slate-400">{selectedConv.routing_decision.alternative_owner}</span>
                    </div>
                  )}
                  <div className="pt-2 border-t border-slate-800/80 text-slate-300 leading-relaxed text-[11px]">
                    <strong>Rationale: </strong>{selectedConv.routing_decision.reason}
                  </div>
                </div>
              </div>
            )}

            {/* Raw Transcript with Offset View */}
            {selectedConv.raw_text && (
              <div className="space-y-2">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">Raw Source Text / Transcript</h4>
                <div className="bg-slate-950 p-3.5 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-300 whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
                  {selectedConv.raw_text}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Manual Override Modal */}
      <Modal
        isOpen={overrideModalOpen}
        onClose={() => setOverrideModalOpen(false)}
        title="Override Routing Assignment"
      >
        <form onSubmit={handleOverrideSubmit} className="space-y-4 text-xs">
          <div>
            <label className="block text-slate-300 font-medium mb-1">New Target Owner</label>
            <select
              value={overrideOwnerId}
              onChange={(e) => setOverrideOwnerId(Number(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
            >
              <option value={2}>Marcus Vance (Commercial Lead)</option>
              <option value={3}>Elena Rostova (Commercial AE)</option>
              <option value={5}>David Kim (Renewal Specialist)</option>
              <option value={6}>Priya Patel (Solutions Architect)</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-300 font-medium mb-1">Override Reason (Audited)</label>
            <textarea
              required
              rows={3}
              value={overrideReason}
              onChange={(e) => setOverrideReason(e.target.value)}
              placeholder="Explain why this conversation is reassigned manually..."
              className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={() => setOverrideModalOpen(false)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={overrideSubmitting}
              className="px-4 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-50"
            >
              {overrideSubmitting ? 'Saving...' : 'Confirm Override'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
