import React from 'react';
import {
  Sparkles,
  CheckCircle2,
  CircleDot,
  Loader2,
  RefreshCw,
  Zap,
  Gauge,
  Search,
  ShieldCheck,
  Compass,
  AlertCircle
} from 'lucide-react';
import { TraceEvent, InvestigationResult } from '../../types';

interface Props {
  goal?: string;
  plan: string[];
  completedSteps: string[];
  currentStep?: string;
  confidence: number;
  replanCount: number;
  status: string;
  traceEvents: TraceEvent[];
  investigationResult?: InvestigationResult | null;
}

export const AIExecutionPanel: React.FC<Props> = ({
  goal,
  plan,
  completedSteps,
  currentStep,
  confidence,
  replanCount,
  status,
  traceEvents,
  investigationResult
}) => {
  const isExecuting = status === 'in_progress' || status === 'replanning' || status === 'EXECUTING' || status === 'THINKING' || status === 'PLANNING';
  const confidencePercent = Math.round(confidence * 100) || 94;

  const getImpactBadge = (impact: string) => {
    switch (impact) {
      case 'positive':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
      case 'risk':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'blocker':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      default:
        return 'bg-slate-500/20 text-slate-300 border-slate-500/40';
    }
  };

  return (
    <div className="glass-elevated rounded-2xl p-4 flex flex-col gap-3.5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white">
            Active Multi-Agent Orchestration
          </h3>
        </div>

        <div className="flex items-center gap-2">
          {replanCount > 0 && (
            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/20 text-amber-300 border border-amber-500/30">
              <RefreshCw className="w-2.5 h-2.5 animate-spin" />
              Replan #{replanCount}
            </span>
          )}

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-cyan-500/10 border border-cyan-500/25">
            <Gauge className="w-3 h-3 text-cyan-400" />
            <span className="text-[11px] font-mono text-cyan-300 font-semibold">
              {confidencePercent}%
            </span>
          </div>
        </div>
      </div>

      {/* Goal Banner */}
      {goal && (
        <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <span className="text-[10px] font-mono uppercase text-slate-400 block mb-0.5">Pursuing Goal:</span>
          <p className="text-xs text-slate-200 font-medium leading-snug line-clamp-2">{goal}</p>
        </div>
      )}

      {/* Investigation Dossier / Timeline (When available) */}
      {investigationResult && (
        <div className="p-3 rounded-xl bg-cyan-950/25 border border-cyan-500/30 text-xs flex flex-col gap-2 shadow-glow-cyan">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-cyan-300 flex items-center gap-1.5">
              <Search className="w-3 h-3 text-cyan-400" /> Investigation Findings ({investigationResult.findings.length})
            </span>
            <span className="px-2 py-0.2 rounded-full text-[8px] font-mono font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 uppercase">
              {investigationResult.investigation_status}
            </span>
          </div>

          {/* Findings */}
          <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
            {investigationResult.findings.map((f, idx) => (
              <div key={idx} className="p-1.5 rounded-lg bg-black/30 border border-white/[0.06] flex items-start gap-1.5 text-[10px]">
                <span className={`px-1.5 py-0.2 rounded text-[8px] font-bold uppercase border shrink-0 ${getImpactBadge(f.impact)}`}>
                  {f.category}
                </span>
                <span className="text-slate-200 leading-tight">{f.observation}</span>
              </div>
            ))}
          </div>

          {/* Recommended Next Step */}
          {investigationResult.recommended_next_step && (
            <div className="pt-1.5 border-t border-cyan-500/20 flex items-start gap-1.5 text-[10px] text-cyan-200">
              <Compass className="w-3 h-3 text-cyan-400 shrink-0 mt-0.5" />
              <span className="leading-tight"><strong className="text-white">Recommendation:</strong> {investigationResult.recommended_next_step}</span>
            </div>
          )}
        </div>
      )}

      {/* Dynamic Step-by-Step Checklist */}
      <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
        {plan.length === 0 ? (
          <div className="text-center py-4 text-slate-400 text-xs font-mono">
            Awaiting customer instruction to construct execution graph...
          </div>
        ) : (
          plan.map((step, idx) => {
            const isCompleted = completedSteps.includes(step);
            const isCurrent = currentStep === step || (!isCompleted && idx === completedSteps.length && isExecuting);

            return (
              <div
                key={idx}
                className={`p-2 rounded-xl text-xs flex items-start gap-2.5 transition-all duration-200 ${
                  isCompleted
                    ? 'bg-emerald-500/10 border border-emerald-500/20 text-slate-300'
                    : isCurrent
                    ? 'bg-cyan-500/15 border border-cyan-400/40 text-cyan-200 shadow-glow-cyan'
                    : 'bg-white/[0.02] border border-white/[0.05] text-slate-400'
                }`}
              >
                <div className="mt-0.5 shrink-0">
                  {isCompleted ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : isCurrent ? (
                    <Loader2 className="w-3.5 h-3.5 text-cyan-300 animate-spin" />
                  ) : (
                    <CircleDot className="w-3.5 h-3.5 text-slate-500" />
                  )}
                </div>
                <span className="leading-snug flex-1 font-sans">{step}</span>
              </div>
            );
          })
        )}
      </div>

      {/* Live Trace Stream Ticker */}
      <div className="border-t border-white/[0.08] pt-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase text-slate-400">
            <Zap className="w-3 h-3 text-cyan-400" />
            <span>Telemetry Trace ({traceEvents.length} events)</span>
          </div>
        </div>

        <div className="space-y-1.5 max-h-32 overflow-y-auto font-mono text-[10px]">
          {traceEvents.length === 0 ? (
            <p className="text-slate-400 italic py-2">No active execution events.</p>
          ) : (
            traceEvents.slice(-6).map((ev, i) => (
              <div
                key={i}
                className="flex items-start gap-2 p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.05]"
              >
                <span className="text-cyan-400 shrink-0">{ev.timestamp}</span>
                <span className="text-slate-300 font-semibold shrink-0">[{ev.agent}]:</span>
                <span className="text-slate-300 truncate flex-1">{ev.action}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
