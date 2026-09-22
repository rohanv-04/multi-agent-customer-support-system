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
