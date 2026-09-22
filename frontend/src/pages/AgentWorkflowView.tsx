import React from 'react';
import { Network, Bot, ArrowDown, ArrowRight, ShieldCheck, Wrench, Search, Brain, FileText, Workflow } from 'lucide-react';
import { AgentInfo } from '../types';

interface Props {
  agents: AgentInfo[];
  onSelectAgent: (agentId: string) => void;
}

export const AgentWorkflowView: React.FC<Props> = ({ agents, onSelectAgent }) => {
  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-10">
      <div className="glass-elevated rounded-3xl p-6 sm:p-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 rounded-2xl bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 shadow-glow-cyan">
            <Network className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Multi-Agent Workflow Topology</h2>
            <p className="text-xs text-slate-400 font-mono">
              LangGraph State Graph with Dynamic Routing, Verification Gateways & Replanning Loops
            </p>
          </div>
        </div>
      </div>

      {/* Workflow Map Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <div
            key={agent.id}
            onClick={() => onSelectAgent(agent.id)}
            className="glass-standard p-5 rounded-2xl cursor-pointer hover:border-cyan-400/40 hover:scale-[1.01] transition-all group"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="p-2.5 rounded-xl bg-white/[0.04] border border-white/[0.08] text-cyan-300 group-hover:bg-cyan-500/20 transition-colors">
                <Bot className="w-5 h-5" />
              </div>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                {Math.round(agent.confidence_avg * 100)}% Confidence
              </span>
            </div>

            <h3 className="text-base font-bold text-white group-hover:text-cyan-200 transition-colors">
              {agent.name}
            </h3>
            <p className="text-xs text-cyan-300/80 font-mono mb-2">{agent.role}</p>

            <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed mb-4">
              {agent.purpose}
            </p>

            <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-slate-400 font-mono">
              <span>{agent.tools_accessible.length} Capabilities</span>
              <span className="text-cyan-400 group-hover:underline">Inspect Node →</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
