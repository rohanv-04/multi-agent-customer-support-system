import React from 'react';
import {
  Sparkles,
  CheckCircle2,
  CircleDot,
  Loader2,
  RefreshCw,
  Zap,
  Gauge
} from 'lucide-react';
import { TraceEvent } from '../../types';

interface Props {
  goal?: string;
  plan: string[];
  completedSteps: string[];
  currentStep?: string;
  confidence: number;
  replanCount: number;
  status: string;
  traceEvents: TraceEvent[];
}

export const AIExecutionPanel: React.FC<Props> = ({
  goal,
  plan,
  completedSteps,
  currentStep,
  confidence,
  replanCount,
  status,
  traceEvents
}) => {
  const isExecuting = status === 'in_progress' || status === 'replanning';
  const confidencePercent = Math.round(confidence * 100) || 94;

  return (
    <div className="glass-elevated rounded-2xl p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400 animate-pulse" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-white">
            Active AI Task Execution
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

      {/* Dynamic Step-by-Step Checklist */}
      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {plan.length === 0 ? (
          <div className="text-center py-6 text-slate-400 text-xs font-mono">
            Awaiting customer instruction to construct DAG plan...
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

        <div className="space-y-1.5 max-h-36 overflow-y-auto font-mono text-[10px]">
          {traceEvents.length === 0 ? (
            <p className="text-slate-400 italic py-2">No active execution events.</p>
          ) : (
            traceEvents.slice(-5).map((ev, i) => (
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
