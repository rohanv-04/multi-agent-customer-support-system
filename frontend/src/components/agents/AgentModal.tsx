import React from 'react';
import { X, Bot, ShieldCheck, Wrench, CheckCircle, Cpu } from 'lucide-react';
import { AgentInfo } from '../../types';

interface Props {
  agent: AgentInfo | null;
  onClose: () => void;
}

export const AgentModal: React.FC<Props> = ({ agent, onClose }) => {
  if (!agent) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md animate-fadeIn">
      <div className="glass-floating rounded-3xl p-6 w-full max-w-lg relative border border-white/20 shadow-2xl">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] text-slate-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-500/30 to-blue-600/30 border border-cyan-400/40 flex items-center justify-center text-cyan-300 shadow-glow-cyan">
            <Bot className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">{agent.name}</h3>
            <p className="text-xs text-cyan-300 font-mono">{agent.role}</p>
          </div>
        </div>

        {/* Operational Purpose */}
        <div className="mb-4 p-3 rounded-2xl bg-white/[0.03] border border-white/[0.07]">
          <span className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block mb-1">
            Agent Purpose & Mandate
          </span>
          <p className="text-xs text-slate-200 leading-relaxed font-sans">{agent.purpose}</p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 gap-3 mb-4">
          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07]">
            <span className="text-[10px] text-slate-400 font-mono block mb-0.5">Status</span>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Active Node
            </div>
          </div>

          <div className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.07]">
            <span className="text-[10px] text-slate-400 font-mono block mb-0.5">Average Confidence</span>
            <span className="text-xs font-mono font-bold text-cyan-300">
              {Math.round(agent.confidence_avg * 100)}%
            </span>
          </div>
        </div>

        {/* Tools Accessible */}
        <div>
          <div className="flex items-center gap-1.5 text-xs font-semibold uppercase text-slate-300 mb-2">
            <Wrench className="w-3.5 h-3.5 text-cyan-400" />
            <span>Tools & Execution Capabilities</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {agent.tools_accessible.map((tool, i) => (
              <span
                key={i}
                className="px-2.5 py-1 rounded-xl bg-cyan-500/10 border border-cyan-500/25 text-[11px] font-mono text-cyan-300"
              >
                {tool}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
