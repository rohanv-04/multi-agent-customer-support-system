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

export interface OrderSummary {
  order_id: string;
  status: string;
  total_amount: number;
  items?: any[];
  carrier?: string;
  tracking_number?: string;
  delay_reason?: string;
}

export interface EscalationTicket {
  ticket_id: string;
  customer_id: string;
  task_id?: string;
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
  confidence?: number;
  status?: string;
  execution_trace?: TraceEvent[];
  plan?: string[];
  completed_steps?: string[];
  tool_calls?: any[];
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
