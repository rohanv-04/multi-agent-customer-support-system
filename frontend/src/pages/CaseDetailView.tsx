import React, { useState, useEffect, useRef } from 'react';
import { 
  ArrowLeft, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  Send, 
  Sparkles, 
  ShieldCheck, 
  ShieldAlert, 
  User, 
  Package, 
  Activity, 
  FileText, 
  Check, 
  X, 
  RefreshCw,
  Cpu,
  CornerDownRight,
  ExternalLink,
  Lock,
  Brain,
  MessageSquare
} from 'lucide-react';
import { 
  getCaseDetail, 
  getCaseTimeline, 
  getCaseTrace, 
  getCustomer360, 
  addCaseMessage, 
  updateCaseStatus, 
  reviewActionRequest,
  sendMessage,
  getCaseDNA,
  getNextBestAction,
  getCaseConflicts,
  getSimilarCases
} from '../services/api';
import { 
  CaseDNA, 
  NextBestActionResponse, 
  AgentDebateRecord, 
  SimilarCaseItem,
  TimelineItem
} from '../types';
import { useAuth } from '../context/AuthContext';

interface Props {
  caseId: string;
  onBack: () => void;
}

export const CaseDetailView: React.FC<Props> = ({ caseId, onBack }) => {
  const { user, hasPermission } = useAuth();
  const [caseDetail, setCaseDetail] = useState<any | null>(null);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [trace, setTrace] = useState<any | null>(null);
  const [customer360, setCustomer360] = useState<any | null>(null);
  const [caseDNA, setCaseDNA] = useState<CaseDNA | null>(null);
  const [nextAction, setNextAction] = useState<NextBestActionResponse | null>(null);
  const [debates, setDebates] = useState<AgentDebateRecord[]>([]);
  const [similarCases, setSimilarCases] = useState<SimilarCaseItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeRightTab, setActiveRightTab] = useState<'trace' | 'dna' | 'nba' | 'debates' | 'similar' | 'evidence' | 'decision' | 'actions'>('trace');
  const [timelineFilter, setTimelineFilter] = useState<'all' | 'message' | 'event' | 'action' | 'agent_run' | 'escalation'>('all');
  const [messageDirection, setMessageDirection] = useState<'outbound' | 'internal'>('outbound');
  const timelineEndRef = useRef<HTMLDivElement>(null);
  
  // Reply input state
  const [replyMessage, setReplyMessage] = useState<string>('');
  const [isSending, setIsSending] = useState<boolean>(false);
  const [isResolving, setIsResolving] = useState<boolean>(false);

  const fetchFullCaseContext = async () => {
    setIsLoading(true);
    try {
      const [detailRes, timeRes, traceRes, dnaRes, nbaRes, debateRes, simRes] = await Promise.all([
        getCaseDetail(caseId).catch(() => null),
        getCaseTimeline(caseId).catch(() => []),
        getCaseTrace(caseId).catch(() => null),
        getCaseDNA(caseId).catch(() => null),
        getNextBestAction(caseId).catch(() => null),
        getCaseConflicts(caseId).catch(() => ({ conflicts: [] })),
        getSimilarCases(caseId).catch(() => ({ similar_cases: [] }))
      ]);

      setCaseDetail(detailRes);
      setTimeline(timeRes || []);
      setTrace(traceRes);
      setCaseDNA(dnaRes);
      setNextAction(nbaRes);
      setDebates(debateRes?.conflicts || []);
      setSimilarCases(simRes?.similar_cases || []);

      if (detailRes?.customer_id) {
        const c360 = await getCustomer360(detailRes.customer_id).catch(() => null);
        setCustomer360(c360);
      }
    } catch (err) {
      console.error('Failed to load case context:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchFullCaseContext();
  }, [caseId]);

  useEffect(() => {
    timelineEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [timeline]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyMessage.trim() || isSending) return;

    setIsSending(true);
    try {
      await addCaseMessage(caseId, {
        body: replyMessage,
        direction: messageDirection,
        channel: caseDetail?.channel || 'web_chat',
        sender_type: 'agent',
        sender_id: user?.email || 'agent'
      });
      setReplyMessage('');
      fetchFullCaseContext();
    } catch (err) {
      console.error('Failed to dispatch message:', err);
    } finally {
      setIsSending(false);
    }
  };

  const [actionNotice, setActionNotice] = useState<{ message: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [isProcessingAction, setIsProcessingAction] = useState<boolean>(false);

  const handleAiSolve = async () => {
    setIsResolving(true);
    try {
      await sendMessage(
        caseDetail?.description || caseDetail?.subject,
        caseDetail?.customer_id || 'CUST1002',
        caseDetail?.conversation_id,
        caseId
      );
      fetchFullCaseContext();
    } catch (err) {
      console.error('AI execution failed:', err);
    } finally {
      setIsResolving(false);
    }
  };

  const handleActionApproval = async (actionId: string, approved: boolean, reason?: string) => {
    if (!hasPermission('actions:approve')) {
      setActionNotice({
        message: 'Permission denied: Only supervisors or admins can approve operational actions.',
        type: 'error'
      });
      return;
    }

    const actionVerb = approved ? 'approve and execute' : 'reject';
    if (!window.confirm(`Are you sure you want to ${actionVerb} this operational action?`)) {
      return;
    }

    setIsProcessingAction(true);
    setActionNotice({ message: `Submitting ${actionVerb}...`, type: 'info' });
    try {
      await reviewActionRequest(
        actionId,
        approved ? 'approved' : 'rejected',
        user?.name || user?.email || 'Supervisor',
        reason || (approved ? 'Authorized by supervisor via operations console' : 'Rejected during manual triage'),
        caseId
      );
      setActionNotice({
        message: `Action successfully ${approved ? 'approved and executed' : 'rejected'}.`,
        type: 'success'
      });
      await fetchFullCaseContext();
    } catch (err: any) {
      console.error('Approval failed:', err);
      setActionNotice({
        message: `Approval failed: ${err.message || 'Server error'}`,
        type: 'error'
      });
    } finally {
      setIsProcessingAction(false);
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    try {
      await updateCaseStatus(caseId, newStatus, user?.name || 'Agent');
      fetchFullCaseContext();
    } catch (err) {
      console.error('Status transition error:', err);
    }
  };

  const now = new Date();
  const isBreached = caseDetail?.sla_deadline && new Date(caseDetail.sla_deadline) < now && !['RESOLVED', 'CLOSED'].includes(caseDetail.status);

  return (
    <div className="p-4 md:p-6 space-y-4 max-w-[1800px] mx-auto min-h-[calc(100vh-6rem)] flex flex-col">
      {/* Top Workspace Navigation & Case Header */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 backdrop-blur-md flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onBack}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-all"
            title="Back to Case Queue"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-cyan-400">{caseDetail?.id || caseId}</span>
              <span className="text-slate-500">•</span>
              <h1 className="text-base font-bold text-white truncate max-w-xl">{caseDetail?.subject || 'Support Case Workspace'}</h1>
            </div>
            <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
              <span>Channel: <strong className="text-slate-200 capitalize">{caseDetail?.channel}</strong></span>
              <span>•</span>
              <span>Priority: <strong className="text-slate-200 uppercase">{caseDetail?.priority}</strong></span>
              <span>•</span>
              <span>Tenant: <strong className="text-cyan-400 font-mono">{caseDetail?.organization_id}</strong></span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Status Lifecycle Transition */}
          <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-1.5">
            <span className="text-xs text-slate-400 font-medium">Status:</span>
            <select
              value={caseDetail?.status || 'TRIAGING'}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="bg-transparent text-xs text-cyan-300 font-bold focus:outline-none cursor-pointer"
            >
              <option value="NEW" className="bg-slate-900 text-white">NEW</option>
              <option value="TRIAGING" className="bg-slate-900 text-white">TRIAGING</option>
              <option value="INVESTIGATING" className="bg-slate-900 text-white">INVESTIGATING</option>
              <option value="DECISION_PENDING" className="bg-slate-900 text-white">DECISION PENDING</option>
              <option value="ACTION_PENDING" className="bg-slate-900 text-white">ACTION PENDING</option>
              <option value="VERIFYING" className="bg-slate-900 text-white">VERIFYING</option>
              <option value="RESOLVED" className="bg-slate-900 text-emerald-400">RESOLVED</option>
              <option value="ESCALATED" className="bg-slate-900 text-red-400">ESCALATED</option>
              <option value="CLOSED" className="bg-slate-900 text-slate-400">CLOSED</option>
            </select>
          </div>

          <button
            onClick={fetchFullCaseContext}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl transition-all"
            title="Refresh Case"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* 3-COLUMN ENTERPRISE WORKSPACE */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 flex-1 items-start">
        {/* ========================================================= */}
        {/* LEFT COLUMN: Customer 360 & Case Dossier (3 of 12 cols) */}
        {/* ========================================================= */}
        <div className="lg:col-span-3 space-y-4">
          {/* Customer Profile Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-cyan-400" />
                Customer Dossier
              </span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                {customer360?.loyalty?.tier || caseDetail?.customer_tier || 'Standard'}
              </span>
            </div>

            <div className="space-y-1">
              <div className="text-sm font-bold text-white">{customer360?.profile?.name || caseDetail?.customer_name || caseDetail?.customer_id}</div>
              <div className="text-xs text-slate-400 truncate">{customer360?.profile?.email || caseDetail?.customer_email || 'Verified Customer'}</div>
              <div className="text-xs text-slate-400 font-mono">{caseDetail?.customer_id}</div>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800/80 text-xs">
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Lifetime Spend</div>
                <div className="font-semibold text-emerald-400 font-mono">
                  ${customer360?.loyalty?.lifetime_spend?.toFixed(2) || '0.00'}
                </div>
              </div>
              <div>
                <div className="text-[10px] text-slate-500 uppercase">Past Orders</div>
                <div className="font-semibold text-white">
                  {customer360?.loyalty?.order_count || 0} Orders
                </div>
              </div>
            </div>
          </div>

          {/* Active SLA & Priority Gauge */}
          <div className={`border rounded-2xl p-5 backdrop-blur-md space-y-3 ${
            isBreached ? 'bg-red-950/20 border-red-500/40' : 'bg-slate-900/80 border-slate-800'
          }`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-amber-400" />
                SLA Compliance
              </span>
              {isBreached ? (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">
                  BREACHED
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  ON TRACK
                </span>
              )}
            </div>

            <div className="space-y-1">
              <div className="text-xs text-slate-400">Target Resolution Deadline:</div>
              <div className="text-sm font-mono font-bold text-white">
                {caseDetail?.sla_deadline ? new Date(caseDetail.sla_deadline).toLocaleString() : 'Standard 4-Hour SLA'}
              </div>
            </div>

            <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-800">
              <span className="text-slate-400">Customer Sentiment:</span>
              <span className={`font-semibold capitalize ${
                caseDetail?.sentiment === 'frustrated' ? 'text-red-400' :
                caseDetail?.sentiment === 'negative' ? 'text-amber-400' :
                'text-emerald-400'
              }`}>
                {caseDetail?.sentiment || 'Neutral'}
              </span>
            </div>
          </div>

          {/* Order Details (if associated) */}
          {customer360?.orders && customer360.orders.length > 0 && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Package className="w-3.5 h-3.5 text-purple-400" />
                  Recent Order Context
                </span>
              </div>

              {customer360.orders.slice(0, 2).map((ord: any) => (
                <div key={ord.order_id} className="p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50 space-y-1 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-cyan-300">{ord.order_id}</span>
                    <span className={`px-1.5 py-0.2 rounded text-[10px] font-semibold ${
                      ord.status === 'Delayed' ? 'bg-amber-500/20 text-amber-300' :
                      ord.status === 'Refunded' ? 'bg-purple-500/20 text-purple-300' :
                      'bg-slate-700 text-slate-300'
                    }`}>
                      {ord.status}
                    </span>
                  </div>
                  <div className="text-slate-400">${ord.total_amount?.toFixed(2)} • Tracking: <span className="font-mono text-slate-200">{ord.tracking_number || 'N/A'}</span></div>
                </div>
              ))}
            </div>
          )}

          {/* Verified Customer Facts & Memories */}
          {customer360?.memories && customer360.memories.length > 0 && (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md space-y-3">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Brain className="w-3.5 h-3.5 text-cyan-400" />
                Verified Customer Memory
              </span>
              <div className="space-y-2">
                {customer360.memories.map((m: any, idx: number) => (
                  <div key={idx} className="p-2 rounded-lg bg-slate-800/40 text-xs text-slate-300 leading-relaxed border-l-2 border-cyan-500">
                    {m.value}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ========================================================= */}
        {/* CENTER COLUMN: Chronological Case Timeline (5 of 12 cols) */}
        {/* ========================================================= */}
        <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-2xl flex flex-col h-[760px] backdrop-blur-md overflow-hidden">
          {/* Timeline Header & Filter Bar */}
          <div className="p-3.5 border-b border-slate-800 bg-slate-800/30 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-white">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span>Operational Case Timeline & Conversation</span>
              </div>
              <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 px-2 py-0.5 rounded-full">
                {timeline.length} events logged
              </span>
            </div>

            {/* Filter Pills */}
            <div className="flex items-center gap-1 overflow-x-auto text-[10px] font-mono pt-1">
              {[
                { key: 'all', label: 'All Events' },
                { key: 'message', label: 'Messages' },
                { key: 'event', label: 'Lifecycle' },
                { key: 'action', label: 'Actions' },
                { key: 'agent_run', label: 'Agent Runs' },
                { key: 'escalation', label: 'Escalations' }
              ].map((f) => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setTimelineFilter(f.key as any)}
                  className={`px-2.5 py-1 rounded-lg transition-all ${
                    timelineFilter === f.key
                      ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                      : 'bg-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-700/80'
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          {/* Timeline Event Feed */}
          <div className="flex-1 p-4 overflow-y-auto space-y-3.5">
            {timeline
              .filter((item) => {
                if (timelineFilter === 'all') return true;
                const itType = item.item_type || item.type;
                return itType === timelineFilter;
              })
              .map((item, idx) => {
                const itemType = item.item_type || item.type || 'event';

                if (itemType === 'message') {
                  const isCustomer = item.sender_type === 'customer' || 
                    item.actor?.toLowerCase().includes('cust') || 
                    item.title?.toLowerCase().includes('customer') ||
                    item.status === 'inbound';
                  const isInternal = item.status === 'internal' || 
                    item.title?.toLowerCase().includes('internal');

                  return (
                    <div key={idx} className={`flex flex-col ${isCustomer ? 'items-start' : 'items-end'}`}>
                      <div className="text-[10px] text-slate-400 mb-1 px-1 flex items-center gap-1.5 font-mono">
                        <span className="font-semibold text-slate-300">
                          {isInternal ? 'Specialist Note' : isCustomer ? 'Customer' : 'Support Specialist'}
                        </span>
                        {item.badge && (
                          <span className="px-1.5 py-0.2 rounded bg-slate-800 text-[9px] text-cyan-400 border border-slate-700">
                            {item.badge}
                          </span>
                        )}
                        <span>•</span>
                        <span>{new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <div className={`p-3.5 rounded-2xl max-w-[88%] text-xs leading-relaxed ${
                        isInternal
                          ? 'bg-amber-950/30 text-amber-200 border border-amber-600/40 rounded-tr-sm'
                          : isCustomer 
                          ? 'bg-slate-800 text-slate-200 border border-slate-700/80 rounded-tl-sm' 
                          : 'bg-cyan-600/20 text-cyan-100 border border-cyan-500/30 rounded-tr-sm'
                      }`}>
                        {item.body || item.description}
                      </div>
                    </div>
                  );
                } else if (itemType === 'event') {
                  return (
                    <div key={idx} className="flex items-center gap-3 my-2 text-xs">
                      <div className="h-px bg-slate-800 flex-1" />
                      <div className="px-3 py-1 rounded-full bg-slate-800/90 text-slate-300 font-mono text-[10px] border border-slate-700/80 flex items-center gap-1.5 shadow-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                        <span className="font-semibold text-white">{item.title}:</span>
                        <span>{item.summary || item.description}</span>
                        {item.actor && <span className="text-slate-500">({item.actor})</span>}
                      </div>
                      <div className="h-px bg-slate-800 flex-1" />
                    </div>
                  );
                } else if (itemType === 'action') {
                  return (
                    <div key={idx} className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs space-y-1">
                      <div className="flex items-center justify-between font-semibold text-purple-300">
                        <span className="flex items-center gap-1.5">
                          <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
                          <span>{item.title || `Action: ${item.action_type}`}</span>
                        </span>
                        <div className="flex items-center gap-2">
                          {item.metadata?.duration_ms && (
                            <span className="text-[10px] font-mono text-slate-400">{item.metadata.duration_ms}ms</span>
                          )}
                          <span className="text-[10px] text-emerald-400 font-mono uppercase bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-800/40">
                            {item.status || 'completed'}
                          </span>
                        </div>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">{item.output_summary || item.description}</p>
                    </div>
                  );
                } else if (itemType === 'agent_run') {
                  return (
                    <div key={idx} className="p-3 rounded-xl bg-cyan-950/20 border border-cyan-800/30 text-xs space-y-1">
                      <div className="flex items-center justify-between font-semibold text-cyan-300">
                        <span className="flex items-center gap-1.5">
                          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
                          <span>{item.title || `Agent Run: ${item.actor}`}</span>
                        </span>
                        <div className="flex items-center gap-2">
                          {item.metadata?.confidence && (
                            <span className="text-[10px] font-mono text-slate-400">
                              {Math.round(item.metadata.confidence * 100)}% conf
                            </span>
                          )}
                          <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded border ${
                            item.status === 'completed'
                              ? 'text-emerald-400 bg-emerald-950/60 border-emerald-800/40'
                              : 'text-amber-400 bg-amber-950/60 border-amber-800/40'
                          }`}>
                            {item.badge || item.status}
                          </span>
                        </div>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">{item.description || item.summary}</p>
                    </div>
                  );
                } else if (itemType === 'escalation') {
                  return (
                    <div key={idx} className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs space-y-1.5">
                      <div className="flex items-center justify-between font-semibold text-rose-300">
                        <span className="flex items-center gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
                          <span>{item.title}</span>
                        </span>
                        <span className="text-[10px] text-rose-300 uppercase font-mono bg-rose-950/80 px-2 py-0.5 rounded border border-rose-800/60">
                          {item.badge || 'Urgent Escalation'}
                        </span>
                      </div>
                      <p className="text-slate-200 text-[11px] leading-relaxed">{item.description || item.summary}</p>
                      {item.metadata?.assigned_to && (
                        <div className="text-[10px] font-mono text-slate-400 flex items-center gap-1">
                          <span>Assigned Agent:</span>
                          <strong className="text-white">{item.metadata.assigned_to}</strong>
                        </div>
                      )}
                    </div>
                  );
                }

                // Generic Fallback
                return (
                  <div key={idx} className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 text-xs space-y-1">
                    <div className="flex items-center justify-between font-semibold text-slate-300">
                      <span>{item.title}</span>
                      <span className="text-[10px] font-mono text-slate-400">{item.status}</span>
                    </div>
                    <p className="text-slate-400 text-[11px]">{item.description}</p>
                  </div>
                );
              })}

            {timeline.length === 0 && (
              <div className="text-center py-24 text-xs text-slate-500 flex flex-col items-center gap-2">
                <MessageSquare className="w-8 h-8 text-slate-600 stroke-1" />
                <span>No conversation events recorded yet.</span>
              </div>
            )}

            <div ref={timelineEndRef} />
          </div>

          {/* Response / Dispatch Bar */}
          <div className="p-4 border-t border-slate-800 bg-slate-900/90 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 font-medium">Compose Response:</span>
                <div className="flex items-center bg-slate-800 rounded-lg p-0.5 border border-slate-700">
                  <button
                    type="button"
                    onClick={() => setMessageDirection('outbound')}
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-all ${
                      messageDirection === 'outbound'
                        ? 'bg-cyan-500 text-slate-950 shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Customer Reply
                  </button>
                  <button
                    type="button"
                    onClick={() => setMessageDirection('internal')}
                    className={`px-2 py-0.5 rounded text-[10px] font-semibold transition-all ${
                      messageDirection === 'internal'
                        ? 'bg-amber-500 text-slate-950 shadow-sm'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Specialist Note
                  </button>
                </div>
              </div>

              <button
                type="button"
                onClick={handleAiSolve}
                disabled={isResolving}
                className="flex items-center gap-1.5 px-3 py-1 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-xs font-bold shadow-md shadow-cyan-500/20 disabled:opacity-50 transition-all"
              >
                <Sparkles className="w-3.5 h-3.5" />
                {isResolving ? 'AI Processing...' : 'AI Autonomous Triage'}
              </button>
            </div>

            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                value={replyMessage}
                onChange={(e) => setReplyMessage(e.target.value)}
                placeholder={
                  messageDirection === 'internal'
                    ? 'Write internal specialist triage note...'
                    : 'Type customer message or dispatch update...'
                }
                className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              />
              <button
                type="submit"
                disabled={isSending || !replyMessage.trim()}
                className="p-2.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl disabled:opacity-50 transition-all shadow-md"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>

        {/* ========================================================= */}
        {/* RIGHT COLUMN: AI Intelligence & Action Gateway (4 of 12)   */}
        {/* ========================================================= */}
        <div className="lg:col-span-4 bg-slate-900/80 border border-slate-800 rounded-2xl flex flex-col h-[760px] backdrop-blur-md overflow-hidden">
          {/* Tab Navigation */}
          <div className="flex items-center border-b border-slate-800 bg-slate-800/40 p-1 overflow-x-auto gap-1">
            <button
              onClick={() => setActiveRightTab('trace')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-all ${
                activeRightTab === 'trace' ? 'bg-cyan-500 text-slate-950 shadow-md font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              AI Trace
            </button>
            <button
              onClick={() => setActiveRightTab('dna')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-all ${
                activeRightTab === 'dna' ? 'bg-cyan-500 text-slate-950 shadow-md font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Case DNA
            </button>
            <button
              onClick={() => setActiveRightTab('nba')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-all ${
                activeRightTab === 'nba' ? 'bg-cyan-500 text-slate-950 shadow-md font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Next Best Action
            </button>
            <button
              onClick={() => setActiveRightTab('debates')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-all ${
                activeRightTab === 'debates' ? 'bg-cyan-500 text-slate-950 shadow-md font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Debates ({debates.length})
            </button>
            <button
              onClick={() => setActiveRightTab('similar')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-all ${
                activeRightTab === 'similar' ? 'bg-cyan-500 text-slate-950 shadow-md font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Similar ({similarCases.length})
            </button>
            <button
              onClick={() => setActiveRightTab('evidence')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-all ${
                activeRightTab === 'evidence' ? 'bg-cyan-500 text-slate-950 shadow-md font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Evidence
            </button>
            <button
              onClick={() => setActiveRightTab('actions')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg whitespace-nowrap transition-all ${
                activeRightTab === 'actions' ? 'bg-cyan-500 text-slate-950 shadow-md font-bold' : 'text-slate-400 hover:text-white'
              }`}
            >
              Actions
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-5 overflow-y-auto space-y-4">
            {/* TAB 1: AI TRACE TREE */}
            {activeRightTab === 'trace' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Multi-Agent Cognitive Loop</span>
                  <span className="text-[11px] font-mono text-cyan-400">{trace?.tree_nodes?.length || 0} Stages</span>
                </div>

                <div className="space-y-3 relative before:absolute before:left-3.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
                  {trace?.tree_nodes?.map((node: any, idx: number) => (
                    <div key={idx} className="relative pl-8 space-y-1">
                      <span className="absolute left-2 top-1.5 w-3 h-3 rounded-full bg-cyan-500 ring-4 ring-slate-900" />
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-white">{node.agent_name}</span>
                        <span className="text-slate-400 font-mono text-[10px]">{node.latency_ms}ms</span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed bg-slate-800/40 p-2 rounded-lg border border-slate-700/50">
                        {node.output_summary}
                      </p>
                    </div>
                  ))}

                  {(!trace || !trace.tree_nodes || trace.tree_nodes.length === 0) && (
                    <div className="text-center py-16 text-xs text-slate-500">
                      Trigger 'AI Autonomous Triage' to view real-time agent execution trace.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: CASE DNA FINGERPRINT */}
            {activeRightTab === 'dna' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Case DNA Fingerprint</span>
                  <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                    {caseDNA?.fingerprint_hash?.slice(0, 12) || 'HASH-ACTIVE'}
                  </span>
                </div>

                {caseDNA ? (
                  <div className="space-y-3 text-xs">
                    <div className="grid grid-cols-2 gap-2">
                      <div className="p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50">
                        <div className="text-[10px] text-slate-400 uppercase">Intent</div>
                        <div className="font-bold text-white capitalize">{caseDNA.intent?.replace(/_/g, ' ')}</div>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50">
                        <div className="text-[10px] text-slate-400 uppercase">Urgency</div>
                        <div className="font-bold text-amber-400 uppercase">{caseDNA.urgency}</div>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50">
                        <div className="text-[10px] text-slate-400 uppercase">Policy Complexity</div>
                        <div className="font-bold text-purple-300 capitalize">{caseDNA.policy_complexity}</div>
                      </div>
                      <div className="p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50">
                        <div className="text-[10px] text-slate-400 uppercase">Operational Risk</div>
                        <div className="font-bold text-emerald-400 uppercase">{caseDNA.operational_risk}</div>
                      </div>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700/50 space-y-2">
                      <div className="text-[10px] font-semibold text-cyan-400 uppercase font-mono">
                        Activated Agent Capabilities
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {caseDNA.required_capabilities?.map((cap, idx) => (
                          <span key={idx} className="px-2 py-0.5 rounded-md bg-cyan-500/15 border border-cyan-500/30 text-[10px] font-mono text-cyan-300">
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-16 text-xs text-slate-500">
                    Case DNA fingerprint will be calculated upon agent triage.
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: NEXT-BEST-ACTION ENGINE */}
            {activeRightTab === 'nba' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Next-Best-Action Proposals</span>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    Safe Routing
                  </span>
                </div>

                {nextAction ? (
                  <div className="space-y-3 text-xs">
                    <div className="p-3.5 rounded-xl bg-gradient-to-tr from-cyan-950/40 to-slate-800/80 border border-cyan-500/40 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-white text-sm">{nextAction.recommended_action}</span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-cyan-500/20 text-cyan-300">
                          Primary
                        </span>
                      </div>
                      <p className="text-slate-300 text-[11px] leading-relaxed">
                        {nextAction.justification}
                      </p>
                      <div className="pt-2 border-t border-slate-700/60 flex items-center justify-between text-[10px] font-mono">
                        <span className="text-slate-400">Policy: <strong className="text-slate-200">{nextAction.policy_basis}</strong></span>
                        <span className="text-emerald-400 font-bold">{nextAction.risk_level} RISK</span>
                      </div>
                    </div>

                    {nextAction.alternatives && nextAction.alternatives.length > 0 && (
                      <div className="space-y-2 pt-2">
                        <span className="text-[10px] font-semibold text-slate-400 uppercase font-mono">Alternative Remedies</span>
                        {nextAction.alternatives.map((alt, idx) => (
                          <div key={idx} className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-700/40 space-y-1">
                            <div className="flex items-center justify-between font-semibold text-slate-200">
                              <span>{alt.label || alt.action_type}</span>
                              <span className="text-cyan-400 font-mono text-[10px]">{Math.round(alt.confidence * 100)}% Match</span>
                            </div>
                            <p className="text-[11px] text-slate-400">{alt.reason}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-16 text-xs text-slate-500">
                    No active Next-Best-Action proposal calculated.
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: AGENT DEBATE & CONFLICT RESOLUTION */}
            {activeRightTab === 'debates' && (
              <div className="space-y-4">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Multi-Agent Debate Log</span>

                <div className="space-y-3 text-xs">
                  {debates.map((d, idx) => (
                    <div key={idx} className="p-3.5 rounded-xl bg-slate-800/50 border border-slate-700/60 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-amber-300">Debate Resolved by {d.resolved_by}</span>
                        <span className="text-[10px] font-mono text-slate-400">
                          {new Date(d.timestamp).toLocaleTimeString()}
                        </span>
                      </div>

                      {d.conflicting_points && d.conflicting_points.length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[10px] text-slate-400 uppercase font-mono">Contested Points:</span>
                          {d.conflicting_points.map((pt, pIdx) => (
                            <div key={pIdx} className="text-[11px] text-slate-300 bg-slate-900/60 p-2 rounded border border-slate-800">
                              • {pt}
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-500/30 text-[11px] text-emerald-200">
                        <strong>Resolution Rationale:</strong> {d.resolution_rationale}
                      </div>
                    </div>
                  ))}

                  {debates.length === 0 && (
                    <div className="text-center py-16 text-xs text-slate-500">
                      No agent conflicts or debate records for this case. Consensus achieved.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 5: SIMILAR CASES EVIDENCE */}
            {activeRightTab === 'similar' && (
              <div className="space-y-4">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Historical Case Matches</span>

                <div className="space-y-2.5 text-xs">
                  {similarCases.map((sim, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-cyan-300">{sim.case_id}</span>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-cyan-500/15 text-cyan-300 font-mono border border-cyan-500/30">
                          {Math.round(sim.similarity_score * 100)}% Match
                        </span>
                      </div>
                      <div className="font-semibold text-slate-200">{sim.subject}</div>
                      <p className="text-[11px] text-slate-400 leading-snug">
                        {sim.resolution_summary || 'Resolved with standard operational workflow.'}
                      </p>
                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-700/40 font-mono">
                        <span>Outcome: <strong className="text-emerald-400">{sim.outcome || 'RESOLVED'}</strong></span>
                        <span>{sim.was_escalated ? 'Escalated' : 'Autonomous'}</span>
                      </div>
                    </div>
                  ))}

                  {similarCases.length === 0 && (
                    <div className="text-center py-16 text-xs text-slate-500">
                      No historical precedent cases found.
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 6: EVIDENCE & TOOLS */}
            {activeRightTab === 'evidence' && (
              <div className="space-y-4">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Diagnostic Evidence Dossier</span>
                
                <div className="space-y-3">
                  <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-2 text-xs">
                    <div className="flex items-center justify-between font-semibold text-cyan-300">
                      <span>Order & Shipment Intelligence</span>
                      <span className="text-emerald-400 font-mono">Verified Tool</span>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed">
                      Carrier tracking checked against NovaExpress live database. Order status verified as active delayed transit.
                    </p>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-2 text-xs">
                    <div className="flex items-center justify-between font-semibold text-purple-300">
                      <span>Corporate Policy Citations</span>
                      <span className="text-cyan-400 font-mono">RAG Grounded</span>
                    </div>
                    <p className="text-slate-300 text-[11px] leading-relaxed">
                      Evaluated against NovaCart Shipping, Fulfillment & Tracking Policy (Section 3: Delivery Delays & Lost Goods).
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 7: ACTIONS & GATEWAY APPROVALS */}
            {activeRightTab === 'actions' && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Action Gateway Operations</span>
                  <span className="text-[10px] font-mono text-purple-400">Protected Gateway</span>
                </div>

                <div className="space-y-3">
                  <div className="p-4 rounded-xl bg-slate-800/80 border border-slate-700 space-y-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white">Issue Compensation Voucher</span>
                      <span className="text-emerald-400 font-semibold font-mono">AUTO-EXECUTED</span>
                    </div>
                    <p className="text-slate-300 text-[11px]">
                      $15.00 courtesy credit applied for shipment delay compliance.
                    </p>

                    {hasPermission('actions:approve') && (
                      <div className="flex items-center gap-2 pt-2 border-t border-slate-700/60">
                        <button
                          onClick={() => handleActionApproval('ACT-DEMO', true)}
                          className="flex-1 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded-lg text-xs font-bold flex items-center justify-center gap-1 transition-all"
                        >
                          <Check className="w-3.5 h-3.5" /> Approve Override
                        </button>
                        <button
                          onClick={() => handleActionApproval('ACT-DEMO', false)}
                          className="flex-1 py-1.5 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 rounded-lg text-xs font-bold flex items-center justify-center gap-1 transition-all"
                        >
                          <X className="w-3.5 h-3.5" /> Reject
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
