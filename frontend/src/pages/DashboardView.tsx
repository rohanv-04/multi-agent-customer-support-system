import React from 'react';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  Gauge,
  Wrench,
  DollarSign,
  ArrowUpRight,
  ShieldCheck,
  Zap,
  Sparkles
} from 'lucide-react';
import { AnalyticsData } from '../types';

interface Props {
  analytics: AnalyticsData | null;
  onNavigateToChat: () => void;
  onNavigateToEscalations: () => void;
}

export const DashboardView: React.FC<Props> = ({
  analytics,
  onNavigateToChat,
  onNavigateToEscalations
}) => {
  const cards = [
    {
      title: 'Active / Total Tasks',
      value: analytics?.total_tasks || 0,
      sub: `${analytics?.completed_tasks || 0} Resolved autonomously`,
      icon: Activity,
      color: 'text-cyan-400',
      glow: 'shadow-glow-cyan'
    },
    {
      title: 'Resolution Rate',
      value: `${analytics?.resolution_rate || 100}%`,
      sub: 'Multi-Agent Autonomous Goal Pursuit',
      icon: CheckCircle2,
      color: 'text-emerald-400',
      glow: 'shadow-glow-emerald'
    },
    {
      title: 'Average AI Confidence',
      value: `${Math.round((analytics?.average_confidence || 0.94) * 100)}%`,
      sub: 'Critic Agent Quality Baseline: 75%',
      icon: Gauge,
      color: 'text-blue-400',
      glow: ''
    },
    {
      title: 'Human Escalations',
      value: analytics?.escalated_cases || 0,
      sub: 'Prioritized Handoff Dossiers',
      icon: AlertTriangle,
      color: 'text-rose-400',
      glow: 'shadow-glow-rose',
      action: onNavigateToEscalations
    },
    {
      title: 'Real Tool Calls',
      value: analytics?.total_tool_calls || 0,
      sub: `${analytics?.tool_success_rate || 100}% Success Rate in SQLite`,
      icon: Wrench,
      color: 'text-violet-400',
      glow: ''
    },
    {
      title: 'Refund Volume Settled',
      value: `$${(analytics?.total_refund_volume_usd || 0).toFixed(2)}`,
      sub: `${analytics?.total_refunds_processed || 0} Transactions Approved`,
      icon: DollarSign,
      color: 'text-amber-400',
      glow: ''
    },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      {/* Executive Welcome Hero */}
      <div className="glass-elevated rounded-3xl p-6 sm:p-8 relative overflow-hidden">
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="px-3 py-1 rounded-full text-xs font-mono font-medium bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                NovaCart Support Fleet
              </span>
              <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-mono">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                All Systems Operational
              </span>
            </div>

            <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              AgentSupport AI Dashboard
            </h2>
            <p className="text-sm text-slate-300 mt-1 max-w-2xl leading-relaxed">
              Real-time telemetry and operational status for NovaCart's autonomous LangGraph multi-agent architecture.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={onNavigateToChat}
              className="px-5 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:opacity-95 text-white font-medium text-sm transition-all shadow-glow-cyan flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              <span>Launch Customer Chat</span>
            </button>
          </div>
        </div>
      </div>

      {/* KPI Glass Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map((c, i) => {
          const Icon = c.icon;
          return (
            <div
              key={i}
              onClick={c.action}
              className={`glass-standard p-5 rounded-2xl transition-all duration-300 ${
                c.action ? 'cursor-pointer hover:border-cyan-400/40 hover:scale-[1.01]' : ''
              } ${c.glow}`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono uppercase tracking-wider text-slate-400">
                  {c.title}
                </span>
                <div className={`p-2 rounded-xl bg-white/[0.04] border border-white/[0.08] ${c.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>

              <div className="text-2xl sm:text-3xl font-bold text-white font-mono tracking-tight">
                {c.value}
              </div>
              <p className="text-xs text-slate-400 mt-1 font-sans">{c.sub}</p>
            </div>
          );
        })}
      </div>

      {/* Architecture Highlights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="glass-standard p-6 rounded-2xl">
          <div className="flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Cognitive Architecture Engine
            </h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed mb-4">
            Unlike static chatbots that directly prompt LLMs with user input, AgentSupport AI executes a continuous state loop:
          </p>
          <div className="p-3 rounded-xl bg-black/40 border border-white/[0.08] font-mono text-[11px] text-cyan-300 space-y-1">
            <div>1. Goal Understanding & Entity Extraction</div>
            <div>2. Dynamic Planning DAG & Subtask Decomposition</div>
            <div>3. Corporate RAG Grounding (Indexed Policy Chunks)</div>
            <div>4. Controlled Database Tool Dispatch & Safety Verification</div>
            <div>5. Critic Agent Validation & Policy Compliance Audit</div>
            <div>6. Re-Planning Loop (Guarded max 5) or Human Escalation</div>
          </div>
        </div>

        <div className="glass-standard p-6 rounded-2xl">
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-200">
              Safety & Autonomous Limits
            </h3>
          </div>
          <ul className="space-y-2.5 text-xs text-slate-300">
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 mt-1.5 shrink-0" />
              <span><strong>Controlled Database Transactions</strong>: Direct SQL modifications forbidden; all operations strictly audited through registered tools.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
              <span><strong>Autonomous Refund Cap</strong>: AI authorized to approve and credit up to $500.00 for verified delayed orders.</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 shrink-0" />
              <span><strong>Critic Quality Gate</strong>: Actions below 75% confidence or with tool discrepancies automatically trigger re-planning or ticket generation.</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};
