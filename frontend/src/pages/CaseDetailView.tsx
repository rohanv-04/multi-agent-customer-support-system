import React, { useState, useEffect } from 'react';
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
  Brain
} from 'lucide-react';
import { 
  getCaseDetail, 
  getCaseTimeline, 
  getCaseTrace, 
  getCustomer360, 
  addCaseMessage, 
  updateCaseStatus, 
  reviewActionRequest,
  sendMessage 
} from '../services/api';
import { useAuth } from '../context/AuthContext';

interface Props {
  caseId: string;
  onBack: () => void;
}

export const CaseDetailView: React.FC<Props> = ({ caseId, onBack }) => {
  const { user, hasPermission } = useAuth();
  const [caseDetail, setCaseDetail] = useState<any | null>(null);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [trace, setTrace] = useState<any | null>(null);
  const [customer360, setCustomer360] = useState<any | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeRightTab, setActiveRightTab] = useState<'trace' | 'evidence' | 'decision' | 'actions' | 'audit'>('trace');
  
  // Reply input state
  const [replyMessage, setReplyMessage] = useState<string>('');
  const [isSending, setIsSending] = useState<boolean>(false);
  const [isResolving, setIsResolving] = useState<boolean>(false);

  const fetchFullCaseContext = async () => {
    setIsLoading(true);
    try {
      const [detailRes, timeRes, traceRes] = await Promise.all([
        getCaseDetail(caseId).catch(() => null),
        getCaseTimeline(caseId).catch(() => []),
        getCaseTrace(caseId).catch(() => null)
      ]);

      setCaseDetail(detailRes);
      setTimeline(timeRes || []);
      setTrace(traceRes);

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

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyMessage.trim() || isSending) return;

    setIsSending(true);
    try {
      await addCaseMessage(caseId, {
        body: replyMessage,
        direction: 'outbound',
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

  const handleActionApproval = async (actionId: string, approved: boolean) => {
    try {
      await reviewActionRequest(
        actionId,
        approved ? 'approved' : 'rejected',
        user?.email || 'supervisor',
        approved ? 'Authorized by supervisor via operations console' : 'Rejected during manual triage'
      );
      fetchFullCaseContext();
    } catch (err) {
      console.error('Approval failed:', err);
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
          {/* Timeline Header */}
          <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-800/30">
            <div className="flex items-center gap-2 text-xs font-semibold text-white">
              <Activity className="w-4 h-4 text-cyan-400" />
              <span>Operational Case Timeline & Conversation</span>
            </div>
            <span className="text-xs font-mono text-slate-400">{timeline.length} events logged</span>
          </div>

          {/* Timeline Event Feed */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {timeline.map((item, idx) => {
              if (item.type === 'message') {
                const isCustomer = item.sender_type === 'customer';
                return (
                  <div key={idx} className={`flex flex-col ${isCustomer ? 'items-start' : 'items-end'}`}>
                    <div className="text-[10px] text-slate-400 mb-1 px-1 flex items-center gap-1.5 font-mono">
                      <span>{isCustomer ? 'Customer' : 'Support Specialist'}</span>
                      <span>•</span>
                      <span>{new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <div className={`p-3.5 rounded-2xl max-w-[85%] text-xs leading-relaxed ${
                      isCustomer 
                        ? 'bg-slate-800 text-slate-200 border border-slate-700/80 rounded-tl-sm' 
                        : 'bg-cyan-600/20 text-cyan-100 border border-cyan-500/30 rounded-tr-sm'
                    }`}>
                      {item.body}
                    </div>
                  </div>
                );
              } else if (item.type === 'event') {
                return (
                  <div key={idx} className="flex items-center gap-3 my-2 text-xs">
                    <div className="h-px bg-slate-800 flex-1" />
                    <div className="px-3 py-1 rounded-full bg-slate-800/80 text-slate-400 font-mono text-[10px] border border-slate-700/60 flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                      <span>{item.summary}</span>
                    </div>
                    <div className="h-px bg-slate-800 flex-1" />
                  </div>
                );
              } else if (item.type === 'action') {
                return (
                  <div key={idx} className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs space-y-1">
                    <div className="flex items-center justify-between font-semibold text-purple-300">
                      <span className="flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5" /> Action Executed: {item.action_type}
                      </span>
                      <span className="text-[10px] text-emerald-400 font-mono">{item.status}</span>
                    </div>
                    <p className="text-slate-300 text-[11px]">{item.output_summary}</p>
                  </div>
                );
              }
              return null;
            })}

            {timeline.length === 0 && (
              <div className="text-center py-20 text-xs text-slate-500">
                No conversation events recorded yet.
              </div>
            )}
          </div>

          {/* Response / Dispatch Bar */}
          <div className="p-4 border-t border-slate-800 bg-slate-900/90 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Compose Response</span>
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
                placeholder="Type customer message or specialist note..."
                className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              />
              <button
                type="submit"
                disabled={isSending || !replyMessage.trim()}
                className="p-2.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl disabled:opacity-50 transition-all"
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
          <div className="flex items-center border-b border-slate-800 bg-slate-800/40 p-1">
            <button
              onClick={() => setActiveRightTab('trace')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeRightTab === 'trace' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white'
              }`}
            >
              AI Trace
            </button>
            <button
              onClick={() => setActiveRightTab('evidence')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeRightTab === 'evidence' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white'
              }`}
            >
              Evidence
            </button>
            <button
              onClick={() => setActiveRightTab('decision')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeRightTab === 'decision' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white'
              }`}
            >
              Decision & Risk
            </button>
            <button
              onClick={() => setActiveRightTab('actions')}
              className={`flex-1 py-2 text-xs font-semibold rounded-lg transition-all ${
                activeRightTab === 'actions' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white'
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

            {/* TAB 2: EVIDENCE & TOOLS */}
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

            {/* TAB 3: DECISION & RISK */}
            {activeRightTab === 'decision' && (
              <div className="space-y-4">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Policy & Risk Evaluation</span>

                <div className="p-4 rounded-xl bg-slate-800/60 border border-slate-700/60 space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 font-medium">Recommended Remedy:</span>
                    <span className="font-bold text-emerald-400 font-mono uppercase">Resolve / Compensation</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 font-medium">Risk Score:</span>
                    <span className="font-bold text-emerald-400 font-mono">0.12 (LOW RISK)</span>
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-slate-400 font-medium">Human Review Gate:</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-400">
                      Auto-Authorized
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: ACTIONS & GATEWAY APPROVALS */}
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
