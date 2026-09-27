import { Customer360, CustomerCaseSummary, OrderSummary } from '../types';

const API_BASE_URL = 'http://localhost:8000';

export async function sendMessage(message: string, customerId: string = 'CUST1002', conversationId?: string, caseId?: string) {
  const res = await fetch(`${API_BASE_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      customer_id: customerId,
      conversation_id: conversationId,
      case_id: caseId,
      stream: false
    })
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.statusText}`);
  }
  return res.json();
}

export function streamChatMessage(
  message: string,
  customerId: string = 'CUST1002',
  conversationId?: string,
  caseId?: string,
  onTraceEvent?: (trace: any) => void,
  onComplete?: (completion: any) => void,
  onError?: (err: any) => void
) {
  fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      customer_id: customerId,
      conversation_id: conversationId,
      case_id: caseId
    })
  }).then(async (response) => {
    if (!response.body) throw new Error('Readable stream not supported');
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        const line = block.trim();
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.replace('data: ', ''));
            if (data.type === 'trace_event' && onTraceEvent) {
              onTraceEvent(data.trace);
            } else if (data.type === 'task_completed' && onComplete) {
              onComplete(data);
            }
          } catch (e) {
            console.error('SSE JSON parse error:', e);
          }
        }
      }
    }
  }).catch((err) => {
    if (onError) onError(err);
  });
}

export async function getCustomer360(customerId: string): Promise<Customer360> {
  const res = await fetch(`${API_BASE_URL}/api/customers/${customerId}/360`);
  if (!res.ok) throw new Error(`Failed to fetch Customer 360: ${res.statusText}`);
  return res.json();
}

export async function getCustomerCases(customerId: string): Promise<CustomerCaseSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/customers/${customerId}/cases`);
  if (!res.ok) throw new Error(`Failed to fetch Customer Cases: ${res.statusText}`);
  return res.json();
}

export async function getCustomerOrders(customerId: string): Promise<OrderSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/customers/${customerId}/orders`);
  if (!res.ok) throw new Error(`Failed to fetch Customer Orders: ${res.statusText}`);
  return res.json();
}

export async function getCustomerActivity(customerId: string): Promise<any[]> {
  const res = await fetch(`${API_BASE_URL}/api/customers/${customerId}/activity`);
  if (!res.ok) throw new Error(`Failed to fetch Customer Activity: ${res.statusText}`);
  return res.json();
}

export async function getTasks(customerId?: string) {
  const url = customerId ? `${API_BASE_URL}/api/tasks?customer_id=${customerId}` : `${API_BASE_URL}/api/tasks`;
  const res = await fetch(url);
  return res.json();
}

export async function getCases(params?: {
  status?: string;
  priority?: string;
  customer_id?: string;
  channel?: string;
  search?: string;
  limit?: number;
  offset?: number;
}) {
  const query = new URLSearchParams();
  if (params?.status && params.status !== 'ALL') query.append('status', params.status);
  if (params?.priority && params.priority !== 'ALL') query.append('priority', params.priority);
  if (params?.customer_id) query.append('customer_id', params.customer_id);
  if (params?.channel && params.channel !== 'ALL') query.append('channel', params.channel);
  if (params?.search) query.append('search', params.search);
  if (params?.limit) query.append('limit', params.limit.toString());
  if (params?.offset) query.append('offset', params.offset.toString());

  const res = await fetch(`${API_BASE_URL}/api/cases?${query.toString()}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch cases: ${res.statusText}`);
  return res.json();
}

export async function getCaseDetail(caseId: string) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch case detail: ${res.statusText}`);
  return res.json();
}

export async function createCase(data: {
  customer_id: string;
  subject: string;
  description?: string;
  priority?: string;
  channel?: string;
  initial_message?: string;
  organization_id?: string;
}) {
  const res = await fetch(`${API_BASE_URL}/api/cases`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to create case: ${res.statusText}`);
  return res.json();
}

export async function getCaseTimeline(caseId: string) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/timeline`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch timeline: ${res.statusText}`);
  return res.json();
}

export async function addCaseMessage(caseId: string, data: {
  body: string;
  direction?: string;
  channel?: string;
  sender_type?: string;
  sender_id?: string;
}) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/messages`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to add message: ${res.statusText}`);
  return res.json();
}

export async function updateCaseStatus(caseId: string, status: string, actor: string = 'Agent') {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify({ status })
  });
  if (!res.ok) throw new Error(`Failed to update status: ${res.statusText}`);
  return res.json();
}

export async function reviewActionRequest(actionId: string, status: string, reviewer: string, reason?: string, caseId?: string) {
  try {
    const cid = caseId || actionId;
    const url = `${API_BASE_URL}/api/cases/${cid}/actions/${actionId}/review?status_choice=${status}${reason ? `&reason=${encodeURIComponent(reason)}` : ''}`;
    const res = await fetch(url, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    if (res.ok) {
      return res.json();
    }
  } catch (e) {
    console.warn('Real review call fallback:', e);
  }
  return { action_id: actionId, status, reviewer, reason };
}

export async function getTaskDetail(taskId: string) {
  const res = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`);
  return res.json();
}

export async function getAgents() {
  const res = await fetch(`${API_BASE_URL}/api/agents`);
  return res.json();
}

export async function getTools() {
  const res = await fetch(`${API_BASE_URL}/api/tools`);
  return res.json();
}

export async function getCustomerMemory(customerId: string) {
  const res = await fetch(`${API_BASE_URL}/api/memory/${customerId}`);
  return res.json();
}

export async function saveCustomerMemory(customerId: string, key: string, value: string, memoryType = 'preference') {
  const res = await fetch(`${API_BASE_URL}/api/memory/${customerId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key, value, memory_type: memoryType })
  });
  return res.json();
}

export async function getEscalations(status?: string) {
  const url = status ? `${API_BASE_URL}/api/escalations?status=${status}` : `${API_BASE_URL}/api/escalations`;
  const res = await fetch(url);
  return res.json();
}

export async function updateEscalationStatus(ticketId: string, status: string, assignedTo?: string) {
  const res = await fetch(`${API_BASE_URL}/api/escalations/${ticketId}/status`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, assigned_to: assignedTo })
  });
  return res.json();
}

export async function getKnowledgeDocs() {
  const res = await fetch(`${API_BASE_URL}/api/knowledge`);
  return res.json();
}

export async function reindexKnowledge() {
  const res = await fetch(`${API_BASE_URL}/api/knowledge/reindex`, { method: 'POST' });
  return res.json();
}

export async function searchKnowledge(query: string, topK = 3) {
  const res = await fetch(`${API_BASE_URL}/api/knowledge/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, top_k: topK })
  });
  return res.json();
}

export async function getAnalytics() {
  const res = await fetch(`${API_BASE_URL}/api/analytics`);
  return res.json();
}

export async function getCustomers() {
  const res = await fetch(`${API_BASE_URL}/api/customers`);
  return res.json();
}

// ----------------- OBSERVABILITY, EVALUATION & AUDIT -----------------

export async function getCaseTrace(caseId: string) {
  const res = await fetch(`${API_BASE_URL}/api/observability/cases/${caseId}/trace`);
  if (!res.ok) throw new Error(`Failed to fetch case trace: ${res.statusText}`);
  return res.json();
}

export async function getAgentPerformance() {
  const res = await fetch(`${API_BASE_URL}/api/observability/agents`);
  if (!res.ok) throw new Error(`Failed to fetch agent performance: ${res.statusText}`);
  return res.json();
}

export async function getToolPerformance() {
  const res = await fetch(`${API_BASE_URL}/api/observability/tools`);
  if (!res.ok) throw new Error(`Failed to fetch tool performance: ${res.statusText}`);
  return res.json();
}

export async function getFailureAnalysis() {
  const res = await fetch(`${API_BASE_URL}/api/observability/failures`);
  if (!res.ok) throw new Error(`Failed to fetch failure analysis: ${res.statusText}`);
  return res.json();
}

export async function getBenchmarks(category?: string) {
  const url = category ? `${API_BASE_URL}/api/evaluations/benchmarks?category=${category}` : `${API_BASE_URL}/api/evaluations/benchmarks`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch benchmarks: ${res.statusText}`);
  return res.json();
}

export async function runEvaluationSuite(categories?: string[], maxCases?: number, name?: string) {
  const res = await fetch(`${API_BASE_URL}/api/evaluations/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ categories, max_cases: maxCases, name })
  });
  if (!res.ok) throw new Error(`Evaluation run failed: ${res.statusText}`);
  return res.json();
}

export async function getEvaluationRuns() {
  const res = await fetch(`${API_BASE_URL}/api/evaluations/runs`);
  if (!res.ok) throw new Error(`Failed to fetch evaluation runs: ${res.statusText}`);
  return res.json();
}

export async function getEvaluationRunDetail(runId: string) {
  const res = await fetch(`${API_BASE_URL}/api/evaluations/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch evaluation run details: ${res.statusText}`);
  return res.json();
}

export async function getAuditLogs(params?: {
  case_id?: string;
  entity_type?: string;
  action?: string;
  actor_type?: string;
  search?: string;
  limit?: number;
  offset?: number;
}) {
  const query = new URLSearchParams();
  if (params?.case_id) query.append('case_id', params.case_id);
  if (params?.entity_type) query.append('entity_type', params.entity_type);
  if (params?.action) query.append('action', params.action);
  if (params?.actor_type) query.append('actor_type', params.actor_type);
  if (params?.search) query.append('search', params.search);
  if (params?.limit) query.append('limit', params.limit.toString());
  if (params?.offset) query.append('offset', params.offset.toString());

  const res = await fetch(`${API_BASE_URL}/api/audit/logs?${query.toString()}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch audit logs: ${res.statusText}`);
  return res.json();
}

// ------------------- Enterprise Auth & RBAC APIs -------------------

let _authToken: string | null = localStorage.getItem('supportos_jwt_token');

export function setAuthToken(token: string | null) {
  _authToken = token;
  if (token) {
    localStorage.setItem('supportos_jwt_token', token);
  } else {
    localStorage.removeItem('supportos_jwt_token');
  }
}

export function getAuthToken(): string | null {
  if (!_authToken) {
    _authToken = localStorage.getItem('supportos_jwt_token');
  }
  return _authToken;
}

export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function loginUser(email: string, password: string, organizationId?: string) {
  const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, organization_id: organizationId })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Authentication failed');
  }
  const data = await res.json();
  setAuthToken(data.access_token);
  return data;
}

export async function getCurrentUser() {
  const res = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch current user: ${res.statusText}`);
  return res.json();
}

export async function switchUserRole(role: string, organizationId: string = 'ORG-NOVACART') {
  const res = await fetch(`${API_BASE_URL}/api/auth/switch-role?role=${role}&organization_id=${organizationId}`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to switch role: ${res.statusText}`);
  const data = await res.json();
  setAuthToken(data.access_token);
  return data;
}

export async function listTenantUsers() {
  const res = await fetch(`${API_BASE_URL}/api/auth/users`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch users: ${res.statusText}`);
  return res.json();
}

export async function createTenantUser(data: { email: string; password: string; name: string; role: string; organization_id?: string }) {
  const res = await fetch(`${API_BASE_URL}/api/auth/users`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'User creation failed');
  }
  return res.json();
}

export async function updateTenantUserRole(userId: string, role: string, isActive?: boolean) {
  const res = await fetch(`${API_BASE_URL}/api/auth/users/${userId}/role`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify({ role, is_active: isActive })
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'User update failed');
  }
  return res.json();
}

export async function listOrganizations() {
  const res = await fetch(`${API_BASE_URL}/api/auth/organizations`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch organizations: ${res.statusText}`);
  return res.json();
}

// ==============================================================================
// SUPPORTOS AI V2 DIFFERENTIATION API CLIENT
// ==============================================================================

export async function getCustomerFriction(customerId: string) {
  const res = await fetch(`${API_BASE_URL}/api/customers/${customerId}/friction`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch customer friction: ${res.statusText}`);
  return res.json();
}

export async function getCaseDNA(caseId: string) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/dna`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch case DNA: ${res.statusText}`);
  return res.json();
}

export async function getNextBestAction(caseId: string) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/next-action`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch next-best-action: ${res.statusText}`);
  return res.json();
}

export async function getSimilarCases(caseId: string) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/similar`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch similar cases: ${res.statusText}`);
  return res.json();
}

export async function getCaseConflicts(caseId: string) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/conflicts`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch agent conflicts: ${res.statusText}`);
  return res.json();
}

export async function getRootCauses() {
  const res = await fetch(`${API_BASE_URL}/api/root-causes`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch root causes: ${res.statusText}`);
  return res.json();
}

export async function getRootCauseById(id: string) {
  const res = await fetch(`${API_BASE_URL}/api/root-causes/${id}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch root cause details: ${res.statusText}`);
  return res.json();
}

export async function getKnowledgeGaps() {
  const res = await fetch(`${API_BASE_URL}/api/knowledge-gaps`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch knowledge gaps: ${res.statusText}`);
  return res.json();
}

export async function getSimulationScenarios() {
  const res = await fetch(`${API_BASE_URL}/api/simulations/scenarios`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch simulation scenarios: ${res.statusText}`);
  return res.json();
}

export async function runSimulation(data: { scenario_id?: string; customer_id?: string; issue_description: string; system_conditions?: any }) {
  const res = await fetch(`${API_BASE_URL}/api/simulations`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data)
  });
  if (!res.ok) throw new Error(`Failed to execute simulation: ${res.statusText}`);
  return res.json();
}

export async function getSimulationRun(runId: string) {
  const res = await fetch(`${API_BASE_URL}/api/simulations/${runId}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch simulation run: ${res.statusText}`);
  return res.json();
}

export async function getOperationalInsights() {
  const res = await fetch(`${API_BASE_URL}/api/operations/insights`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch operational insights: ${res.statusText}`);
  return res.json();
}

// ==============================================================================
// HUMAN SUPPORT ESCALATION API CLIENT
// ==============================================================================

export async function requestHumanSupport(caseId: string, customerId?: string, notes?: string) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/human-support`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ customer_id: customerId, notes })
  });
  if (!res.ok) throw new Error(`Failed to request human support: ${res.statusText}`);
  return res.json();
}

export async function recordCallInitiated(caseId: string, assignmentId: string) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/human-support/${assignmentId}/call`, {
    method: 'POST',
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to record call initiation: ${res.statusText}`);
  return res.json();
}

export async function getHumanSupportAssignment(caseId: string) {
  const res = await fetch(`${API_BASE_URL}/api/cases/${caseId}/human-support`, {
    headers: getAuthHeaders()
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`Failed to fetch human support assignment: ${res.statusText}`);
  return res.json();
}


