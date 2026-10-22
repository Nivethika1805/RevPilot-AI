import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  CheckCircle2, Clock, AlertTriangle, ShieldAlert,
  Calendar, User, Plus, RefreshCw, XCircle, MessageSquare,
  FileText, ExternalLink
} from 'lucide-react';
import { apiClient } from '../api/client';
import { FollowUpAction } from '../types';
import { PriorityBadge, StatusBadge } from '../components/Badge';
import { Modal } from '../components/Modal';

export const ActionQueue: React.FC = () => {
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>('open');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [selectedAction, setSelectedAction] = useState<FollowUpAction | null>(null);

  // Modals state
  const [snoozeModalOpen, setSnoozeModalOpen] = useState(false);
  const [snoozeDays, setSnoozeDays] = useState(3);
  const [dismissModalOpen, setDismissModalOpen] = useState(false);
  const [dismissReason, setDismissReason] = useState('');
  const [notesModalOpen, setNotesModalOpen] = useState(false);
  const [noteBody, setNoteBody] = useState('');
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    deal_id: 1,
    title: 'Schedule customer follow-up',
    reason: 'Manual manager follow-up trigger',
    priority: 'high',
    due_date: '2026-10-25',
  });

  const { data: actions = [], isLoading, isFetching } = useQuery({
    queryKey: ['actions', statusFilter, priorityFilter],
    queryFn: () => apiClient.getActions({
      status: statusFilter || undefined,
      priority: priorityFilter || undefined,
    }),
  });

  const patchMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => apiClient.patchAction(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
      setSnoozeModalOpen(false);
      setDismissModalOpen(false);
      setSelectedAction(null);
    },
  });

  const noteMutation = useMutation({
    mutationFn: ({ id, body }: { id: number; body: string }) => apiClient.addActionNote(id, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
      setNoteBody('');
    },
  });

  const regenMutation = useMutation({
    mutationFn: () => apiClient.regenerateActions(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
      queryClient.invalidateQueries({ queryKey: ['dashboardMetrics'] });
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: any) => apiClient.createAction(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
      setCreateModalOpen(false);
    },
  });

  const handleComplete = (action: FollowUpAction) => {
    patchMutation.mutate({
      id: action.id,
      data: { status: 'completed' },
    });
  };

  const handleSnooze = () => {
    if (!selectedAction) return;
    const snoozeDate = new Date();
    snoozeDate.setDate(snoozeDate.getDate() + snoozeDays);
    patchMutation.mutate({
      id: selectedAction.id,
      data: {
        status: 'snoozed',
        snoozed_until: snoozeDate.toISOString(),
      },
    });
  };

  const handleDismiss = () => {
    if (!selectedAction || !dismissReason.trim()) return;
    patchMutation.mutate({
      id: selectedAction.id,
      data: {
        status: 'dismissed',
        dismissed_reason: dismissReason,
      },
    });
  };

  const handleAddNote = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAction || !noteBody.trim()) return;
    noteMutation.mutate({
      id: selectedAction.id,
      body: noteBody,
    });
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Action Queue</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/20 text-accent border border-accent/30">
              Evidence to Action
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Prioritized daily actions generated from risk signals, stalled deals, overdue replies, and renewal deadlines.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => regenMutation.mutate()}
            disabled={regenMutation.isPending}
            className="btn-secondary text-xs flex items-center gap-1.5"
            title="Re-evaluate deal signals and refresh recommended actions"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${regenMutation.isPending ? 'animate-spin' : ''}`} />
            Regenerate
          </button>
          <button
            onClick={() => setCreateModalOpen(true)}
            className="btn-primary text-xs flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" />
            New Action
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-border bg-card/60 backdrop-blur-sm">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold uppercase text-muted-foreground tracking-wider mr-1">Status:</span>
          {['open', 'in_progress', 'completed', 'snoozed', 'dismissed', 'all'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status === 'all' ? '' : status)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                (statusFilter === status || (status === 'all' && !statusFilter))
                  ? 'bg-accent text-accent-foreground shadow-sm'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {status.replace('_', ' ').charAt(0).toUpperCase() + status.replace('_', ' ').slice(1)}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase text-muted-foreground tracking-wider">Priority:</span>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-card border border-border rounded px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-accent"
          >
            <option value="">All Priorities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Actions Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-12 text-center text-sm text-muted-foreground">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-accent" />
            Loading actions...
          </div>
        ) : actions.length === 0 ? (
          <div className="p-12 text-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3 opacity-80" />
            <h3 className="text-base font-semibold text-foreground">No actions found</h3>
            <p className="text-sm text-muted-foreground mt-1 max-w-sm mx-auto">
              There are no {statusFilter || 'active'} actions matching your current filters.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="py-3 px-4 w-10">Done</th>
                  <th className="py-3 px-4">Action & Context</th>
                  <th className="py-3 px-4">Deal / Account</th>
                  <th className="py-3 px-4">Priority</th>
                  <th className="py-3 px-4">Due Date</th>
                  <th className="py-3 px-4">Owner</th>
                  <th className="py-3 px-4 text-right">Operations</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-sm">
                {actions.map((action) => {
                  const isCompleted = action.status === 'completed';
                  const isSnoozed = action.status === 'snoozed';
                  const isDismissed = action.status === 'dismissed';

                  return (
                    <tr
                      key={action.id}
                      className={`hover:bg-muted/20 transition-colors ${isCompleted ? 'opacity-60 bg-muted/10' : ''}`}
                    >
                      {/* Done Checkbox */}
                      <td className="py-3 px-4 align-top pt-4">
                        <button
                          onClick={() => handleComplete(action)}
                          disabled={isCompleted}
                          className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                            isCompleted
                              ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
                              : 'border-border hover:border-accent text-transparent hover:text-accent/50'
                          }`}
                          title={isCompleted ? 'Completed' : 'Mark as completed'}
                        >
                          <CheckCircle2 className="w-3.5 h-3.5" />
                        </button>
                      </td>

                      {/* Action Title & Reason */}
                      <td className="py-3 px-4 align-top max-w-md">
                        <div className="flex items-center gap-2">
                          <span className={`font-semibold ${isCompleted ? 'line-through text-muted-foreground' : 'text-foreground'}`}>
                            {action.title}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded uppercase font-semibold bg-muted text-muted-foreground border border-border">
                            {action.source}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {action.reason}
                        </p>

                        {/* Evidence Chips */}
                        {action.evidence_ids && action.evidence_ids.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {action.evidence_ids.map((ev: any, idx: number) => (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1 text-[10px] font-mono bg-card/80 border border-border/80 px-1.5 py-0.5 rounded text-accent"
                              >
                                <FileText className="w-2.5 h-2.5" />
                                {ev.source_ref || ev.label || `REF-${idx}`}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Dismissed reason or snooze indicator */}
                        {isDismissed && action.dismissed_reason && (
                          <div className="mt-1.5 text-xs text-rose-400/90 italic">
                            Dismissed: {action.dismissed_reason}
                          </div>
                        )}
                        {isSnoozed && action.snoozed_until && (
                          <div className="mt-1.5 text-xs text-amber-400/90 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> Snoozed until {new Date(action.snoozed_until).toLocaleDateString()}
                          </div>
                        )}
                      </td>

                      {/* Deal / Account */}
                      <td className="py-3 px-4 align-top">
                        <div className="flex flex-col">
                          <Link
                            to={`/deals/${action.deal_id}`}
                            className="font-medium text-foreground hover:text-accent transition-colors flex items-center gap-1"
                          >
                            <span>{action.deal_name || `Deal #${action.deal_id}`}</span>
                            <ExternalLink className="w-3 h-3 opacity-60" />
                          </Link>
                          <span className="text-xs text-muted-foreground">
                            {action.account_name} ({action.deal_code})
                          </span>
                        </div>
                      </td>

                      {/* Priority */}
                      <td className="py-3 px-4 align-top">
                        <PriorityBadge priority={action.priority} />
                      </td>

                      {/* Due Date */}
                      <td className="py-3 px-4 align-top text-xs text-muted-foreground whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Calendar className="w-3.5 h-3.5 opacity-70" />
                          <span>{action.due_date ? new Date(action.due_date).toLocaleDateString() : 'None'}</span>
                        </div>
                      </td>

                      {/* Owner */}
                      <td className="py-3 px-4 align-top text-xs text-muted-foreground">
                        <div className="flex items-center gap-1.5">
                          <User className="w-3.5 h-3.5 opacity-70" />
                          <span>{action.owner_name || 'Unassigned'}</span>
                        </div>
                      </td>

                      {/* Operations */}
                      <td className="py-3 px-4 align-top text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => {
                              setSelectedAction(action);
                              setNotesModalOpen(true);
                            }}
                            className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
                            title="Notes"
                          >
                            <MessageSquare className="w-4 h-4" />
                          </button>

                          {!isCompleted && !isDismissed && (
                            <>
                              <button
                                onClick={() => {
                                  setSelectedAction(action);
                                  setSnoozeModalOpen(true);
                                }}
                                className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-amber-400 transition-colors"
                                title="Snooze action"
                              >
                                <Clock className="w-4 h-4" />
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedAction(action);
                                  setDismissReason('');
                                  setDismissModalOpen(true);
                                }}
                                className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-rose-400 transition-colors"
                                title="Dismiss action (reason required)"
                              >
                                <XCircle className="w-4 h-4" />
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Snooze Modal */}
      <Modal
        isOpen={snoozeModalOpen}
        onClose={() => setSnoozeModalOpen(false)}
        title="Snooze Action"
      >
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Temporarily hide <span className="font-semibold text-foreground">"{selectedAction?.title}"</span> from the active queue.
          </p>
          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1.5">
              Snooze Duration
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[1, 3, 7].map((days) => (
                <button
                  key={days}
                  type="button"
                  onClick={() => setSnoozeDays(days)}
                  className={`py-2 px-3 text-xs font-medium rounded-lg border transition-colors ${
                    snoozeDays === days
                      ? 'border-accent bg-accent/20 text-accent font-semibold'
                      : 'border-border bg-card text-muted-foreground hover:bg-muted'
                  }`}
                >
                  {days} {days === 1 ? 'Day' : 'Days'}
                </button>
              ))}
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setSnoozeModalOpen(false)}
              className="btn-secondary text-xs"
            >
              Cancel
            </button>
            <button
              onClick={handleSnooze}
              disabled={patchMutation.isPending}
              className="btn-primary text-xs"
            >
              Confirm Snooze
            </button>
          </div>
        </div>
      </Modal>

      {/* Dismiss Modal */}
      <Modal
        isOpen={dismissModalOpen}
        onClose={() => setDismissModalOpen(false)}
        title="Dismiss Action"
      >
        <div className="space-y-4">
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-xs flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold">Reason is Required for Audit Trail</div>
              Dismissing a recommended action will be logged in the immutable audit history.
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1.5">
              Dismissal Reason *
            </label>
            <textarea
              value={dismissReason}
              onChange={(e) => setDismissReason(e.target.value)}
              placeholder="e.g. Discussed with customer offline, pricing model adjusted, no further action needed..."
              rows={3}
              className="w-full bg-card border border-border rounded-lg p-2.5 text-xs text-foreground focus:ring-1 focus:ring-accent focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setDismissModalOpen(false)}
              className="btn-secondary text-xs"
            >
              Cancel
            </button>
            <button
              onClick={handleDismiss}
              disabled={!dismissReason.trim() || patchMutation.isPending}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-600 text-white hover:bg-rose-500 disabled:opacity-50 transition-colors"
            >
              Dismiss Action
            </button>
          </div>
        </div>
      </Modal>

      {/* Notes Modal */}
      <Modal
        isOpen={notesModalOpen}
        onClose={() => setNotesModalOpen(false)}
        title={`Action Notes: ${selectedAction?.title || ''}`}
      >
        <div className="space-y-4">
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {selectedAction?.notes_list && selectedAction.notes_list.length > 0 ? (
              selectedAction.notes_list.map((note) => (
                <div key={note.id} className="p-2.5 rounded border border-border bg-muted/20 text-xs">
                  <div className="flex justify-between text-muted-foreground text-[10px] mb-1">
                    <span className="font-medium text-foreground">{note.author_name || 'System User'}</span>
                    <span>{new Date(note.created_at).toLocaleString()}</span>
                  </div>
                  <div className="text-foreground">{note.body}</div>
                </div>
              ))
            ) : (
              <div className="text-xs text-muted-foreground text-center py-4">No notes recorded yet.</div>
            )}
          </div>

          <form onSubmit={handleAddNote} className="space-y-2 pt-2 border-t border-border">
            <label className="block text-xs font-semibold uppercase text-muted-foreground">Add Note</label>
            <textarea
              value={noteBody}
              onChange={(e) => setNoteBody(e.target.value)}
              placeholder="Add progress note or customer update..."
              rows={2}
              className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground focus:ring-1 focus:ring-accent focus:outline-none"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={!noteBody.trim() || noteMutation.isPending}
                className="btn-primary text-xs"
              >
                Add Note
              </button>
            </div>
          </form>
        </div>
      </Modal>

      {/* Create Action Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create New Action"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">Deal ID</label>
            <input
              type="number"
              value={createForm.deal_id}
              onChange={(e) => setCreateForm({ ...createForm, deal_id: parseInt(e.target.value) || 1 })}
              className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">Action Title</label>
            <select
              value={createForm.title}
              onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
              className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground"
            >
              <option value="Review pricing proposal">Review pricing proposal</option>
              <option value="Schedule customer follow-up">Schedule customer follow-up</option>
              <option value="Confirm customer requirements">Confirm customer requirements</option>
              <option value="Arrange product demonstration">Arrange product demonstration</option>
              <option value="Escalate to sales manager">Escalate to sales manager</option>
              <option value="Record customer response">Record customer response</option>
              <option value="Custom action">Custom action</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">Reason</label>
            <textarea
              value={createForm.reason}
              onChange={(e) => setCreateForm({ ...createForm, reason: e.target.value })}
              rows={2}
              className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">Priority</label>
              <select
                value={createForm.priority}
                onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground"
              >
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold uppercase text-muted-foreground mb-1">Due Date</label>
              <input
                type="date"
                value={createForm.due_date}
                onChange={(e) => setCreateForm({ ...createForm, due_date: e.target.value })}
                className="w-full bg-card border border-border rounded-lg p-2 text-xs text-foreground"
              >
              </input>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setCreateModalOpen(false)}
              className="btn-secondary text-xs"
            >
              Cancel
            </button>
            <button
              onClick={() => createMutation.mutate(createForm)}
              disabled={createMutation.isPending}
              className="btn-primary text-xs"
            >
              Create Action
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
