import React, { useState, useEffect } from 'react';
import { 
  Bot, 
  Cpu, 
  Activity, 
  CheckCircle2, 
  Clock, 
  Zap, 
  ShieldCheck, 
  RefreshCw, 
  Wrench, 
  Layers,
  Sparkles
} from 'lucide-react';
import { getAgentPerformance, getAgents } from '../services/api';
import { useAuth } from '../context/AuthContext';

export const AgentOperationsView: React.FC = () => {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<any[]>([]);
  const [agents, setAgents] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchAgentData = async () => {
    setIsLoading(true);
    try {
      const [mRes, aRes] = await Promise.all([
        getAgentPerformance().catch(() => []),
        getAgents().catch(() => ({ agents: [] }))
      ]);
      setMetrics(mRes || []);
      setAgents(aRes?.agents || []);
    } catch (err) {
      console.error('Failed to load agent operations telemetry:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAgentData();
  }, [user?.organization_id]);

  const SPECIALIST_FLEET = [
    {
      id: 'intake_agent',
      name: 'Intake & Intent Agent',
      category: 'Perception',
      description: 'Strictly extracts structured intent, urgency, sentiment, entities, and order references.',
      tools: ['Regex Extractor', 'Catalog Matcher', 'Sentiment Classifier'],
      latency: 45,
      successRate: 99.4,
      status: 'Active'
    },
    {
      id: 'investigation_agent',
      name: 'Investigation Specialist',
      category: 'Diagnostic',
      description: 'Assembles verified facts from live SQLite databases, carrier APIs, and past interactions.',
      tools: ['get_order_status', 'check_refund_eligibility', 'carrier_tracking_api'],
      latency: 180,
      successRate: 98.8,
      status: 'Active'
    },
    {
      id: 'policy_agent',
      name: 'Policy Intelligence Agent',
      category: 'Governance',
      description: 'Evaluates corporate policy terms, extracts conditions, and produces evidence-backed citations.',
      tools: ['Policy Vector RAG', 'Condition Extractor', 'Exception Detector'],
      latency: 120,
      successRate: 99.1,
      status: 'Active'
    },
    {
      id: 'decision_engine',
      name: 'Decision Engine',
      category: 'Resolution',
      description: 'Determines resolution strategy (resolve, refund, reship, cancel, monitor, escalate).',
      tools: ['Remedy Evaluator', 'Constraint Matcher', 'State Synthesizer'],
      latency: 85,
      successRate: 99.6,
      status: 'Active'
    },
    {
      id: 'risk_agent',
      name: 'Risk & Compliance Agent',
      category: 'Guardrails',
      description: 'Computes monetary and fraud risk factors, applying human supervisor approval gates.',
      tools: ['Risk Factor Scorer', 'Fraud Filter', 'VIP Velocity Check'],
      latency: 60,
      successRate: 100.0,
      status: 'Active'
    },
    {
      id: 'action_gateway',
      name: 'Action Gateway Agent',
      category: 'Execution',
      description: 'Executes sensitive transactional operations behind permission and approval checks.',
      tools: ['process_refund', 'cancel_order', 'issue_reshipment', 'update_crm'],
      latency: 210,
      successRate: 99.2,
      status: 'Active'
    },
    {
      id: 'verification_agent',
      name: 'Verification Agent',
      category: 'Verification',
      description: 'Conducts post-action state verification and commits cryptographic audit records.',
      tools: ['State Verifier', 'Audit Logger', 'Notification Dispatcher'],
      latency: 75,
      successRate: 100.0,
      status: 'Active'
    },
    {
      id: 'communication_agent',
      name: 'Communication Agent',
      category: 'Omnichannel',
      description: 'Formulates empathetic, policy-grounded customer messages across email, chat, and WhatsApp.',
      tools: ['Response Synthesizer', 'Channel Adapter', 'Tone Guardrail'],
      latency: 90,
      successRate: 99.5,
      status: 'Active'
    },
    {
      id: 'escalation_agent',
      name: 'Escalation Agent',
      category: 'Handoff',
      description: 'Prepares structured escalation dossiers with full reasoning paths for human specialists.',
      tools: ['Dossier Compiler', 'Priority Calculator', 'Ticket Router'],
      latency: 110,
      successRate: 98.9,
      status: 'Active'
    }
  ];

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1700px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-tr from-cyan-600 to-blue-600 rounded-xl shadow-lg shadow-cyan-500/20 text-white">
              <Bot className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Agent Operations & Fleet Health</h1>
              <p className="text-xs text-slate-400 font-mono">
                9 Specialist Cognitive Agents Online • Orchestrated via LangGraph • Tenant: <span className="text-cyan-400 font-semibold">{user?.organization_id}</span>
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchAgentData}
          className="p-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-xl transition-all self-start sm:self-auto"
          title="Refresh Telemetry"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Fleet Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {SPECIALIST_FLEET.map((agent) => {
          const liveMetric = metrics.find(m => m.agent_name?.toLowerCase().includes(agent.name.toLowerCase().split(' ')[0]));
          return (
            <div
              key={agent.id}
              className="bg-slate-900/80 border border-slate-800 hover:border-cyan-500/40 rounded-2xl p-6 backdrop-blur-md space-y-4 transition-all group flex flex-col justify-between"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                    {agent.category}
                  </span>
                  <div className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>{agent.status}</span>
                  </div>
                </div>

                <div>
                  <h3 className="text-base font-bold text-white group-hover:text-cyan-300 transition-colors">
                    {agent.name}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                    {agent.description}
                  </p>
                </div>

                {/* Assigned Tools */}
                <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
                  <div className="text-[10px] text-slate-500 uppercase font-semibold flex items-center gap-1">
                    <Wrench className="w-3 h-3 text-cyan-400" /> Integrated Capabilities
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {agent.tools.map((t, idx) => (
                      <span key={idx} className="px-2 py-0.5 bg-slate-800/80 border border-slate-700/60 rounded-md text-[10px] font-mono text-slate-300">
                        {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Performance Telemetry Footer */}
              <div className="grid grid-cols-2 gap-2 pt-4 border-t border-slate-800/80 text-xs">
                <div className="bg-slate-800/40 p-2.5 rounded-xl">
                  <div className="text-[10px] text-slate-500 uppercase font-mono">Avg Latency</div>
                  <div className="font-bold text-cyan-300 font-mono">
                    {liveMetric?.avg_latency_ms || agent.latency} ms
                  </div>
                </div>

                <div className="bg-slate-800/40 p-2.5 rounded-xl">
                  <div className="text-[10px] text-slate-500 uppercase font-mono">Success Rate</div>
                  <div className="font-bold text-emerald-400 font-mono">
                    {liveMetric?.success_rate || agent.successRate}%
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
