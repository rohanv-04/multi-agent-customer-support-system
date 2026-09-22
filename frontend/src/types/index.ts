export type AIState = 'IDLE' | 'THINKING' | 'PLANNING' | 'EXECUTING' | 'WAITING_FOR_TOOL' | 'VALIDATING' | 'REPLANNING' | 'COMPLETED' | 'ESCALATED' | 'ERROR';

export interface TraceEvent {
  timestamp: string;
  iso_time?: string;
  agent: string;
  action: string;
  details?: any;
  status?: 'completed' | 'running' | 'failed' | 'warning';
}

export interface TaskStep {
  step_number: number;
  description: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  result_summary?: string;
}

export interface ToolCallLog {
  id?: number;
  task_id?: string;
  tool_name: string;
  input: any;
  output: any;
  status: 'success' | 'failure';
  duration_ms: number;
  error_message?: string;
  created_at?: string;
}

export interface Customer {
  customer_id: string;
  name: string;
  email: string;
  phone?: string;
  tier: string;
  account_status: string;
  orders?: OrderSummary[];
}

export interface OrderItem {
  item_id: string;
  name: string;
  qty: number;
  price: number;
}

export interface OrderSummary {
  order_id: string;
  status: string;
  total_amount: number;
  currency?: string;
  items?: OrderItem[];
  carrier?: string;
  tracking_number?: string;
  order_date?: string;
  expected_delivery?: string;
  actual_delivery?: string;
  delay_reason?: string;
}

export interface CustomerPaymentSummary {
  payment_id: string;
  order_id: string;
  amount: number;
  currency: string;
  status: string;
  payment_method: string;
  created_at: string;
}

export interface CustomerRefundSummary {
  refund_id: string;
  order_id: string;
  refund_amount: number;
  currency: string;
  status: string;
  reason: string;
  refund_method: string;
  processed_at: string;
}

export interface CustomerCaseSummary {
  id: string;
  channel: string;
  subject: string;
  priority: string;
  status: string;
  intent?: string;
  sentiment: string;
  created_at: string;
  resolved_at?: string;
}

export interface CustomerComplaintSummary {
  complaint_id: string;
  source_type: string;
  severity: string;
  issue: string;
  status: string;
  created_at: string;
}

export interface CustomerResolutionSummary {
  resolution_id: string;
  case_id?: string;
  order_id?: string;
  resolution_type: string;
  outcome_summary: string;
  resolved_at: string;
}

export interface CustomerMemoryItem {
  id: number;
  memory_type: string;
  key: string;
  value: string;
  updated_at: string;
}

export interface CustomerLoyalty {
  tier: string;
  is_vip: boolean;
  lifetime_spend: number;
  currency: string;
  order_count: number;
  tenure_days: number;
  perks: string[];
}

export interface Customer360 {
  profile: {
    customer_id: string;
    organization_id: string;
    name: string;
    email: string;
    phone?: string;
    account_status: string;
    created_at: string;
  };
  account_status: string;
  loyalty: CustomerLoyalty;
  orders: OrderSummary[];
  payments: CustomerPaymentSummary[];
  refunds: CustomerRefundSummary[];
  previous_cases: CustomerCaseSummary[];
  cases: CustomerCaseSummary[];
  previous_complaints: CustomerComplaintSummary[];
  previous_resolutions: CustomerResolutionSummary[];
  memories: CustomerMemoryItem[];
  open_cases_count: number;
  risk_assessment: {
    risk_level: string;
    churn_signals: string[];
    total_refunded_amount?: number;
    loyalty_score?: number;
    recommended_treatment?: string;
  };
}

export interface InvestigationFinding {
  category: string;
  observation: string;
  impact: string;
  confidence: number;
}

export interface InvestigationEvidence {
  source: string;
  fact: string;
  verified: boolean;
  timestamp?: string;
}

export interface InvestigationResult {
  case_id: string;
  findings: InvestigationFinding[];
  evidence: InvestigationEvidence[];
  data_sources: string[];
  unresolved_questions: string[];
  recommended_next_step: string;
  investigation_status: string;
}

export interface EscalationTicket {
  ticket_id: string;
  customer_id: string;
  task_id?: string;
  case_id?: string;
  summary: string;
  intent?: string;
  reason: string;
  actions_attempted: string[];
  tools_used: string[];
  results: string[];
  status: 'open' | 'in_progress' | 'resolved';
  priority: string;
  recommended_action?: string;
  assigned_to?: string;
  created_at?: string;
  resolved_at?: string;
}

export interface KnowledgeDoc {
  doc_id: string;
  title: string;
  category: string;
  filename: string;
  chunk_count: number;
  last_indexed_at?: string;
}

export interface AnalyticsData {
  total_tasks: number;
  completed_tasks: number;
  escalated_cases: number;
  resolution_rate: number;
  average_confidence: number;
  total_replanning_events: number;
  total_tool_calls: number;
  tool_success_rate: number;
  tool_distribution: Record<string, number>;
  total_refunds_processed: number;
  total_refund_volume_usd: number;
  system_status: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  task_id?: string;
  case_id?: string;
  confidence?: number;
  status?: string;
  execution_trace?: TraceEvent[];
  plan?: string[];
  completed_steps?: string[];
  tool_calls?: any[];
  investigation_result?: InvestigationResult;
  customer_360?: Customer360;
  requires_escalation?: boolean;
  escalation_dossier?: any;
}

export interface AgentInfo {
  id: string;
  name: string;
  role: string;
  status: string;
  confidence_avg: number;
  purpose: string;
  tools_accessible: string[];
}
