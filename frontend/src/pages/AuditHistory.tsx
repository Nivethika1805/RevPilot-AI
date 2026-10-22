import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  History, Search, Filter, ShieldCheck, Eye,
  ArrowRight, RefreshCw, Database, User, Calendar
} from 'lucide-react';
import { apiClient } from '../api/client';
import { AuditEvent } from '../types';
import { Modal } from '../components/Modal';

export const AuditHistory: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [detailModalOpen, setDetailModalOpen] = useState(false);

  const { data: events = [], isLoading, isFetching } = useQuery({
    queryKey: ['auditEvents', eventTypeFilter, entityTypeFilter],
    queryFn: () => apiClient.getAuditEvents({
      event_type: eventTypeFilter || undefined,
      entity_type: entityTypeFilter || undefined,
    }),
  });

  const filteredEvents = events.filter((ev) => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      ev.actor_label?.toLowerCase().includes(term) ||
      ev.event_type?.toLowerCase().includes(term) ||
      ev.entity_type?.toLowerCase().includes(term) ||
      ev.reason?.toLowerCase().includes(term) ||
      ev.correlation_id?.toLowerCase().includes(term)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Immutable Audit History</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-accent/20 text-accent border border-accent/30">
              Append-Only Ledger
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Complete traceability of all system actions: manual overrides, alerts, imports, conflict resolutions, and routing changes.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-border bg-card/60 backdrop-blur-sm">
        <div className="flex items-center gap-2 flex-1 max-w-sm">
          <Search className="w-4 h-4 text-muted-foreground ml-2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search events, actors, correlation IDs..."
            className="w-full bg-transparent text-xs text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="bg-card border border-border rounded px-2.5 py-1 text-xs text-foreground"
          >
            <option value="">All Event Types</option>
            <option value="manual_override">Manual Override</option>
            <option value="alert_transition">Alert Transition</option>
            <option value="conflict_resolution">Conflict Resolution</option>
            <option value="action_created">Action Created</option>
            <option value="action_completed">Action Completed</option>
            <option value="action_dismissed">Action Dismissed</option>
            <option value="import_job_completed">Import Job Completed</option>
            <option value="simulation_commit">Simulation Commit</option>
          </select>

          <select
            value={entityTypeFilter}
            onChange={(e) => setEntityTypeFilter(e.target.value)}
            className="bg-card border border-border rounded px-2.5 py-1 text-xs text-foreground"
          >
            <option value="">All Entity Types</option>
            <option value="deal">Deals</option>
            <option value="conversation">Conversations</option>
            <option value="alert">Alerts</option>
            <option value="action">Actions</option>
            <option value="field_conflict">Conflicts</option>
            <option value="import_job">Import Jobs</option>
          </select>
        </div>
      </div>

      {/* Events Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        {isLoading ? (
          <div className="p-12 text-center text-sm text-muted-foreground">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-accent" />
            Loading audit ledger...
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="p-12 text-center text-sm text-muted-foreground">
            No audit events found matching your query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Event Type</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">Target Entity</th>
                  <th className="py-3 px-4">Reason / Notes</th>
                  <th className="py-3 px-4">Correlation ID</th>
                  <th className="py-3 px-4 text-right">Payload Diff</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {filteredEvents.map((ev) => (
                  <tr key={ev.id} className="hover:bg-muted/20 transition-colors">
                    <td className="py-3 px-4 text-muted-foreground whitespace-nowrap">
                      {new Date(ev.occurred_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 font-mono font-medium text-foreground">
                      <span className="px-2 py-0.5 rounded text-[10px] uppercase font-bold bg-muted border border-border">
                        {ev.event_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-foreground font-medium">
                      <div className="flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-accent opacity-80" />
                        <span>{ev.actor_label}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-mono text-accent">
                        {ev.entity_type} #{ev.entity_id}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground max-w-xs truncate">
                      {ev.reason || 'System operation'}
                    </td>
                    <td className="py-3 px-4 font-mono text-[10px] text-muted-foreground">
                      {ev.correlation_id?.substring(0, 12)}...
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => {
                          setSelectedEvent(ev);
                          setDetailModalOpen(true);
                        }}
                        className="btn-secondary text-[11px] py-1 px-2.5 inline-flex items-center gap-1"
                      >
                        <Eye className="w-3 h-3" />
                        Diff
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Diff Modal */}
      <Modal
        isOpen={detailModalOpen}
        onClose={() => setDetailModalOpen(false)}
        title={`Audit Event #${selectedEvent?.id}: ${selectedEvent?.event_type}`}
      >
        <div className="space-y-4 text-xs">
          <div className="grid grid-cols-2 gap-2 p-3 rounded-lg bg-muted/20 border border-border">
            <div>
              <span className="text-muted-foreground block text-[10px] uppercase">Actor</span>
              <span className="font-semibold text-foreground">{selectedEvent?.actor_label}</span>
            </div>
            <div>
              <span className="text-muted-foreground block text-[10px] uppercase">Timestamp</span>
              <span className="font-semibold text-foreground">
                {selectedEvent ? new Date(selectedEvent.occurred_at).toLocaleString() : ''}
              </span>
            </div>
          </div>

          {selectedEvent?.reason && (
            <div className="p-2.5 rounded bg-card border border-border">
              <span className="font-semibold text-foreground block mb-0.5">Recorded Reason:</span>
              <span className="text-muted-foreground">{selectedEvent.reason}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <span className="font-bold text-rose-400 block mb-1">State Before:</span>
              <pre className="p-2.5 rounded bg-muted/30 border border-border font-mono text-[10px] text-foreground max-h-60 overflow-y-auto">
                {JSON.stringify(selectedEvent?.before || {}, null, 2)}
              </pre>
            </div>
            <div>
              <span className="font-bold text-emerald-400 block mb-1">State After:</span>
              <pre className="p-2.5 rounded bg-muted/30 border border-border font-mono text-[10px] text-foreground max-h-60 overflow-y-auto">
                {JSON.stringify(selectedEvent?.after || {}, null, 2)}
              </pre>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button onClick={() => setDetailModalOpen(false)} className="btn-secondary text-xs">
              Close
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
