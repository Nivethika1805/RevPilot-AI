export interface User {
  id: number;
  email: string;
  name: string;
  role: 'admin' | 'manager' | 'rep' | 'demo_evaluator';
  team_id?: number;
  is_active: boolean;
  created_at: string;
}

export interface Team {
  id: number;
  name: string;
  responsibilities?: string[];
  created_at: string;
}

export interface Account {
  id: number;
  external_id?: string;
  name: string;
  normalized_name: string;
  industry?: string;
  owner_user_id?: number;
  synthetic_flag: boolean;
  created_at: string;
}

export interface Deal {
  id: number;
  external_id?: string;
  deal_code: string;
  account_id: number;
  account_name?: string;
  name: string;
  value: number;
  currency: string;
  stage: string;
  owner_user_id?: number;
  owner_name?: string;
  status: 'open' | 'won' | 'lost';
  expected_close_date?: string;
  renewal_date?: string;
  last_activity_at?: string;
  next_activity_at?: string;
  source_tracks_next_steps: boolean;
  decision_maker_known?: boolean | null;
  created_at: string;
  updated_at: string;
  current_risk_score?: number;
  current_risk_category?: 'Low' | 'Medium' | 'High' | 'Critical';
  data_completeness_pct?: number;
  has_manual_override?: boolean;
  open_alerts_count?: number;
  open_actions_count?: number;
}

export interface EvidenceExcerpt {
  id: number;
  conversation_id: number;
  source_type: string;
  source_ref: string;
  excerpt_text: string;
  start_offset?: number;
  end_offset?: number;
  occurred_at: string;
  extractor: 'rules' | 'llm' | 'manual';
  created_at: string;
}

export interface Finding {
  id: number;
  conversation_id: number;
  kind: 'objection' | 'unresolved_question' | 'competitor_mention' | 'follow_up_commitment' | 'intent' | 'sentiment_indicator';
  label: string;
  status: 'open' | 'resolved';
  evidence_id?: number;
  confidence?: number;
  evidence?: EvidenceExcerpt;
  created_at: string;
}

export interface Conversation {
  id: number;
  external_id?: string;
  deal_id: number;
  account_id: number;
  assigned_user_id?: number;
  type: 'call' | 'meeting' | 'email' | 'note';
  occurred_at: string;
  summary: string;
  customer_intent?: string;
  sentiment_label?: string;
  sentiment_basis?: string;
  urgency: 'low' | 'medium' | 'high' | 'critical';
  priority: 'low' | 'medium' | 'high' | 'critical';
  source_file?: string;
  source_record_ref: string;
  recommended_next_action?: string;
  routing_status: 'recommended' | 'accepted' | 'overridden' | 'unassigned_review';
  created_at: string;
  deal_name?: string;
  account_name?: string;
  assigned_user_name?: string;
  raw_text?: string;
  evidence_excerpts?: EvidenceExcerpt[];
  findings?: Finding[];
  routing_decision?: {
    id: number;
    winning_rule: string;
    recommended_owner: string;
    alternative_owner?: string;
    reason: string;
    status: string;
    override_owner?: string;
    override_reason?: string;
  };
}

export interface Activity {
  id: number;
  external_id?: string;
  deal_id: number;
  user_id?: number;
  type: string;
  occurred_at: string;
  detail: string;
  source_ref: string;
  created_at: string;
  user_name?: string;
}

export interface RiskSignal {
  id: number;
  assessment_id: number;
  signal_code: string;
  state: 'detected' | 'not_detected' | 'unknown';
  severity: 'low' | 'medium' | 'high' | 'critical';
  weight_applied: number;
  score_contribution: number;
  explanation: string;
  why_it_matters: string;
  evidence_ids?: Array<{
    source_ref?: string;
    occurred_at?: string;
    detail?: string;
    label?: string;
  }>;
}

export interface RiskAssessment {
  id: number;
  deal_id: number;
  assessed_at: string;
  as_of: string;
  rules_version: number;
  config_snapshot: Record<string, any>;
  score: number;
  category: 'Low' | 'Medium' | 'High' | 'Critical';
  data_completeness_pct: number;
  confidence_note?: string;
  trigger: string;
  previous_assessment_id?: number;
  is_current: boolean;
  signals: RiskSignal[];
}

export interface Alert {
  id: number;
  deal_id: number;
  assessment_id: number;
  status: 'open' | 'acknowledged' | 'in_progress' | 'resolved' | 'reopened';
  resolution_note?: string;
  resolved_by?: number;
  resolved_by_name?: string;
  resolved_at?: string;
  reopened_reason?: string;
  created_at: string;
}

export interface FollowUpAction {
  id: number;
  deal_id: number;
  deal_name?: string;
  deal_code?: string;
  account_name?: string;
  conversation_id?: number;
  source: 'recommended' | 'manual';
  title: string;
  reason: string;
  evidence_ids?: any[];
  priority: 'low' | 'medium' | 'high' | 'critical';
  owner_user_id?: number;
  owner_name?: string;
  due_date?: string;
  status: 'open' | 'in_progress' | 'completed' | 'snoozed' | 'dismissed' | 'superseded';
  snoozed_until?: string;
  dismissed_reason?: string;
  notes?: string;
  dedupe_key?: string;
  created_at: string;
  completed_at?: string;
  notes_list?: Array<{
    id: number;
    action_id: number;
    author_name?: string;
    body: string;
    created_at: string;
  }>;
}

export interface RoutingRule {
  id: number;
  name: string;
  priority_order: number;
  conditions: Record<string, any>;
  target_owner_user_id?: number;
  target_owner_name?: string;
  target_team_id?: number;
  target_team_name?: string;
  priority_outcome: string;
  enabled: boolean;
  version: number;
  specificity: number;
  created_at: string;
}

export interface FieldConflict {
  id: number;
  entity_type: string;
  entity_id: number;
  entity_label?: string;
  field_name: string;
  current_value?: string;
  incoming_value?: string;
  source_baseline_value?: string;
  import_job_id: number;
  status: 'pending' | 'kept_manual' | 'accepted_source' | 'custom_value';
  resolved_by?: number;
  resolved_at?: string;
  resolution_value?: string;
  created_at: string;
}

export interface FieldProvenance {
  id: number;
  entity_type: string;
  entity_id: number;
  field_name: string;
  source_value?: string;
  current_value?: string;
  previous_source_value?: string;
  is_overridden: boolean;
  last_update_source: string;
  last_import_job_id?: number;
  updated_at: string;
}

export interface AuditEvent {
  id: number;
  occurred_at: string;
  actor_id?: number;
  actor_label: string;
  event_type: string;
  entity_type: string;
  entity_id?: number;
  before?: Record<string, any>;
  after?: Record<string, any>;
  reason?: string;
  import_job_id?: number;
  correlation_id: string;
}

export interface DashboardMetrics {
  as_of: string;
  total_open_pipeline_value: number;
  total_open_deals: number;
  at_risk_deals_count: number;
  high_priority_conversations_count: number;
  overdue_follow_ups_count: number;
  risk_distribution: Record<string, number>;
  stage_distribution: Record<string, { count: number; value: number }>;
  recent_activities: Activity[];
  team_performance: Array<{
    rep_name: string;
    open_deals: number;
    pipeline_value: number;
    overdue_actions: number;
    completed_actions: number;
  }>;
  recent_alerts: Alert[];
  what_should_i_do_today: FollowUpAction[];
}

export interface FindingItem {
  id: string;
  title: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  deal_id?: number;
  deal_code?: string;
  deal_name?: string;
  account_name?: string;
  evidence_refs: Array<{
    source_ref?: string;
    occurred_at?: string;
    detail?: string;
    label?: string;
  }>;
  recommended_action: string;
}

export interface FindingsReport {
  generated_at: string;
  as_of: string;
  findings: FindingItem[];
  difficult_routing_decision?: {
    decision_id: number;
    conversation_ref: string;
    conversation_summary: string;
    deal_code: string;
    chosen_owner: string;
    rejected_alternative: string;
    winning_rule: string;
    reason: string;
    evaluated_rules_count: number;
  };
}
