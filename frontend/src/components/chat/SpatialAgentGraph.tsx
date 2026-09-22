import React from 'react';
import {
  ShieldAlert,
  Brain,
  Search,
  Wrench,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Workflow
} from 'lucide-react';
import { AgentInfo } from '../../types';

interface Props {
  activeAgentName?: string;
  onSelectAgent: (agentId: string) => void;
  agents: AgentInfo[];
}

export const SpatialAgentGraph: React.FC<Props> = ({ activeAgentName, onSelectAgent, agents }) => {
  const getAgentStatus = (id: string, name: string) => {
    if (!activeAgentName) return 'idle';
    const cleanActive = activeAgentName.toLowerCase();
    const cleanName = name.toLowerCase();
    const cleanId = id.toLowerCase();
    if (cleanActive.includes(cleanId) || cleanActive.includes(cleanName.replace(' agent', ''))) {
      return 'active';
    }
    return 'idle';
  };

  const nodes = [
    { id: 'supervisor', name: 'Supervisor Agent', role: 'Master Orchestrator', icon: Workflow, col: 2, row: 1 },
    { id: 'planner', name: 'Planning Agent', role: 'Dynamic Plan DAG', icon: Brain, col: 2, row: 2 },
    { id: 'intent', name: 'Intent Agent', role: 'Goal & Entities', icon: FileText, col: 1, row: 3 },
    { id: 'retrieval', name: 'RAG Agent', role: 'Policy Grounding', icon: Search, col: 2, row: 3 },
    { id: 'resolution', name: 'Resolution Agent', role: 'Tool Dispatcher', icon: Wrench, col: 2, row: 4 },
    { id: 'critic', name: 'Critic Agent', role: 'Validation & Audit', icon: ShieldAlert, col: 2, row: 5 },
  ];

  return (
    <div className="glass-standard rounded-2xl p-4 relative overflow-hidden">
      <div className="flex items-center justify-between mb-3 border-b border-white/[0.08] pb-2">
        <div className="flex items-center gap-2">
          <Workflow className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-200">
            Spatial Agentic Graph
          </h3>
        </div>
        <span className="text-[10px] text-slate-400 font-mono">Live Multi-Agent Routing</span>
      </div>

      {/* Spatial Graph Canvas / Grid */}
      <div className="flex flex-col items-center gap-3 py-2">
        {/* Row 1: Supervisor */}
        {renderNode(nodes[0])}

        <div className="w-0.5 h-4 bg-gradient-to-b from-cyan-400/50 to-blue-500/50" />

        {/* Row 2: Planner */}
        {renderNode(nodes[1])}

        <div className="w-0.5 h-4 bg-gradient-to-b from-blue-500/50 to-violet-500/50" />

        {/* Row 3: Intent & RAG */}
        <div className="grid grid-cols-2 gap-3 w-full max-w-sm">
          {renderNode(nodes[2])}
          {renderNode(nodes[3])}
        </div>

        <div className="w-0.5 h-4 bg-gradient-to-b from-violet-500/50 to-emerald-500/50" />

        {/* Row 4: Resolution */}
        {renderNode(nodes[4])}

        <div className="w-0.5 h-4 bg-gradient-to-b from-emerald-500/50 to-cyan-500/50" />

        {/* Row 5: Critic */}
        {renderNode(nodes[5])}

        {/* Branch: Complete vs Escalate */}
        <div className="grid grid-cols-2 gap-3 w-full max-w-xs mt-1">
          <div className="px-2.5 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/25 flex items-center justify-center gap-1.5 text-[11px] text-emerald-300 font-medium">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Complete</span>
          </div>
          <div className="px-2.5 py-1.5 rounded-xl bg-rose-500/10 border border-rose-500/25 flex items-center justify-center gap-1.5 text-[11px] text-rose-300 font-medium">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>Escalate</span>
          </div>
        </div>
      </div>
    </div>
  );

  function renderNode(node: typeof nodes[0]) {
    const Icon = node.icon;
    const status = getAgentStatus(node.id, node.name);
    const isActive = status === 'active';

    return (
      <button
        key={node.id}
        onClick={() => onSelectAgent(node.id)}
        className={`w-full max-w-[220px] p-2 rounded-xl text-left transition-all duration-300 relative group cursor-pointer ${
          isActive
            ? 'glass-floating bg-cyan-500/20 border-cyan-400 shadow-glow-cyan scale-[1.03] ring-1 ring-cyan-400'
            : 'glass-subtle hover:glass-standard hover:border-white/20'
        }`}
      >
        <div className="flex items-center gap-2">
          <div
            className={`p-1.5 rounded-lg transition-colors ${
              isActive ? 'bg-cyan-500/30 text-cyan-200' : 'bg-white/[0.05] text-slate-400 group-hover:text-slate-200'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between">
              <span className={`text-[11px] font-medium truncate ${isActive ? 'text-cyan-200' : 'text-slate-200'}`}>
                {node.name}
              </span>
              {isActive && (
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
              )}
            </div>
            <p className="text-[9px] text-slate-400 truncate">{node.role}</p>
          </div>
        </div>
      </button>
    );
  }
};
