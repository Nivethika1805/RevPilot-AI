import axios from 'axios';
import {
  DashboardMetrics, Deal, Conversation, FollowUpAction, RoutingRule,
  FieldConflict, FieldProvenance, AuditEvent, FindingsReport, Alert, RiskAssessment
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Auto-attach JWT if stored, or rely on DEMO_MODE fallback
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('revpilot_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const apiClient = {
  // System & Health
  getHealth: async () => (await api.get('/health')).data,
  getSettings: async () => (await api.get('/settings')).data,
  updateRiskConfig: async (signalCode: string, payload: any) =>
    (await api.put(`/settings/risk/${signalCode}`, payload)).data,
  recomputeRisk: async () => (await api.post('/settings/recompute-risk')).data,

  // Dashboard
  getDashboardMetrics: async (params?: { owner_id?: number; stage?: string }): Promise<DashboardMetrics> =>
    (await api.get('/dashboard/metrics', { params })).data,

  // Inbox
  getConversations: async (params?: any): Promise<{ total: number; items: Conversation[]; limit: number; offset: number }> =>
    (await api.get('/conversations', { params })).data,
  getConversationDetail: async (id: number): Promise<Conversation> =>
    (await api.get(`/conversations/${id}`)).data,
  patchConversation: async (id: number, data: any) =>
    (await api.patch(`/conversations/${id}`, data)).data,

  // Deals
  getDeals: async (params?: any): Promise<{ total: number; items: Deal[]; limit: number; offset: number }> =>
    (await api.get('/deals', { params })).data,
  getDealDetail: async (id: number) =>
    (await api.get(`/deals/${id}`)).data,
  patchDeal: async (id: number, data: any) =>
    (await api.patch(`/deals/${id}`, data)).data,
  getDealRiskHistory: async (dealId: number) =>
    (await api.get(`/risk/deal/${dealId}/history`)).data,

  // Risk Replay & Simulation
  replayAssessment: async (assessmentId: number) =>
    (await api.get(`/risk/replay/${assessmentId}`)).data,
  simulateRisk: async (dealId: number, changes: any) =>
    (await api.post('/risk/simulate', { deal_id: dealId, hypothetical_changes: changes })).data,
  commitSimulation: async (dealId: number, changes: any, note: string) =>
    (await api.post('/risk/simulate/commit', { deal_id: dealId, hypothetical_changes: changes, note })).data,

  // Actions
  getActions: async (params?: any): Promise<FollowUpAction[]> =>
    (await api.get('/actions', { params })).data,
  createAction: async (data: any): Promise<FollowUpAction> =>
    (await api.post('/actions', data)).data,
  patchAction: async (id: number, data: any) =>
    (await api.patch(`/actions/${id}`, data)).data,
  addActionNote: async (id: number, body: string) =>
    (await api.post(`/actions/${id}/notes`, { body })).data,
  regenerateActions: async () =>
    (await api.post('/actions/regenerate')).data,

  // Alerts
  transitionAlert: async (id: number, target_status: string, note?: string) =>
    (await api.post(`/alerts/${id}/transition`, { target_status, note })).data,

  // Routing
  getRoutingRules: async (): Promise<RoutingRule[]> =>
    (await api.get('/routing/rules')).data,
  createRoutingRule: async (data: any) =>
    (await api.post('/routing/rules', data)).data,
  updateRoutingRule: async (id: number, data: any) =>
    (await api.put(`/routing/rules/${id}`, data)).data,
  getReviewQueue: async () =>
    (await api.get('/routing/review-queue')).data,
  decideRouting: async (conversationId: number) =>
    (await api.post(`/routing/decide/${conversationId}`)).data,
  overrideRouting: async (conversationId: number, targetOwnerId: number, reason: string) =>
    (await api.post(`/routing/override/${conversationId}`, { target_owner_id: targetOwnerId, reason })).data,
  dryRunRouting: async (conditions: any) =>
    (await api.post('/routing/dry-run', { conditions })).data,

  // Imports & Conflicts
  uploadImportFile: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return (await api.post('/imports/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })).data;
  },
  planImport: async (jobId: number, entityType: string, columnMapping: Record<string, string>) =>
    (await api.post('/imports/plan', { job_id: jobId, entity_type: entityType, column_mapping: columnMapping })).data,
  confirmImport: async (jobId: number, skipInvalidRows = false) =>
    (await api.post('/imports/confirm', { job_id: jobId, skip_invalid_rows: skipInvalidRows })).data,
  getImportReport: async (jobId: number) =>
    (await api.get(`/imports/${jobId}/report`)).data,
  getConflicts: async (): Promise<FieldConflict[]> =>
    (await api.get('/imports/conflicts')).data,
  resolveConflict: async (conflictId: number, choice: 'keep_manual' | 'accept_source' | 'custom_value', customValue?: string) =>
    (await api.post(`/imports/conflicts/${conflictId}/resolve`, { resolution_choice: choice, custom_value: customValue })).data,
  getProvenance: async (entityType: string, entityId: number): Promise<FieldProvenance[]> =>
    (await api.get(`/imports/provenance/${entityType}/${entityId}`)).data,

  // Exports
  createExport: async (format: string, entities: string[]) =>
    (await api.post('/exports/generate', { format, entities })).data,
  getExports: async () =>
    (await api.get('/exports')).data,
  verifyExport: async (exportId: number) =>
    (await api.post(`/exports/${exportId}/verify`)).data,

  // Audit
  getAuditEvents: async (params?: any): Promise<AuditEvent[]> =>
    (await api.get('/audit', { params })).data,

  // Findings
  getFindingsReport: async (): Promise<FindingsReport> =>
    (await api.get('/findings')).data,
};
