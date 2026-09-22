import React, { useState, useEffect } from 'react';
import {
  Activity,
  GitBranch,
  Layers,
  Zap,
  Clock,
  Coins,
  ShieldCheck,
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  CheckCircle2,
  XCircle,
  Wrench,
  Search,
  RefreshCw,
  Cpu
} from 'lucide-react';
import { getCaseTrace, getAgentPerformance, getToolPerformance, getFailureAnalysis } from '../services/api';

export function ObservabilityView() {
  const [activeTab, setActiveTab] = useState<'trace' | 'agents' | 'tools' | 'failures'>('trace');
  const [caseIdInput, setCaseIdInput] = useState('CASE-10001');
  const [traceData, setTraceData] = useState<any | null>(null);
  const [agentMetrics, setAgentMetrics] = useState<any[]>([]);
  const [toolMetrics, setToolMetrics] = useState<any[]>([]);
  const [failureReport, setFailureReport] = useState<any | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({
    intake: true,
    investigation: true,
    decision: true,
    action: true
  });

  const loadTrace = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getCaseTrace(id);
      setTraceData(data);
    } catch (e: any) {
      setError(`Could not find or load execution trace for case "${id}".`);
      setTraceData(null);
    } finally {
      setLoading(false);
    }
  };

  const loadOperationalMetrics = async () => {
    try {
      const [agents, tools, failures] = await Promise.all([
        getAgentPerformance(),
        getToolPerformance(),
        getFailureAnalysis()
      ]);
      setAgentMetrics(agents);
      setToolMetrics(tools);
      setFailureReport(failures);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadTrace(caseIdInput);
    loadOperationalMetrics();
  }, []);

  const toggleNode = (nodeKey: string) => {
    setExpandedNodes(prev => ({ ...prev, [nodeKey]: !prev[nodeKey] }));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-standard rounded-2xl p-5 border border-white/[0.08] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs uppercase tracking-wider mb-1">
            <Activity className="w-4 h-4" />
            <span>SupportOS AI Observability Engine</span>
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            Autonomous Execution Traces & System Telemetry
          </h1>
          <p className="text-slate-400 text-xs">
            Hierarchical cognitive loop traces, tool latency, token cost accounting, and failure diagnostics.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex bg-white/[0.04] p-1 rounded-xl border border-white/[0.06] text-xs">
          <button
            onClick={() => setActiveTab('trace')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'trace'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-glow-cyan'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Case Execution Trace
          </button>
          <button
            onClick={() => setActiveTab('agents')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'agents'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-glow-cyan'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Agent Performance
          </button>
          <button
            onClick={() => setActiveTab('tools')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'tools'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-glow-cyan'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Tool Performance
          </button>
          <button
            onClick={() => setActiveTab('failures')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === 'failures'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 shadow-glow-cyan'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Failure Analysis
          </button>
        </div>
      </div>

      {/* 1. HIERARCHICAL CASE EXECUTION TRACE */}
      {activeTab === 'trace' && (
        <div className="space-y-4">
          {/* Case Search Bar */}
          <div className="glass-card rounded-xl p-3 border border-white/[0.06] flex items-center gap-3">
            <Search className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              value={caseIdInput}
              onChange={(e) => setCaseIdInput(e.target.value)}
              placeholder="Enter Case ID (e.g. CASE-10001)..."
              className="bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none flex-1 font-mono"
            />
            <button
              onClick={() => loadTrace(caseIdInput)}
              className="px-4 py-1.5 rounded-lg bg-cyan-500 text-slate-950 font-semibold text-xs hover:bg-cyan-400 transition-colors flex items-center gap-1.5 shadow-glow-cyan"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              Inspect Trace
            </button>
          </div>

          {error && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {traceData && (
            <div className="space-y-4">
              {/* Summary KPIs */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
                  <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-cyan-400" /> Total Latency
                  </div>
                  <div className="text-lg font-bold text-white mt-1 font-mono">
                    {traceData.total_latency_ms} <span className="text-xs text-slate-400">ms</span>
                  </div>
                </div>

                <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
                  <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5">
                    <Coins className="w-3.5 h-3.5 text-emerald-400" /> Est. Cost
                  </div>
                  <div className="text-lg font-bold text-emerald-400 mt-1 font-mono">
                    ${traceData.total_cost_usd?.toFixed(4)}
                  </div>
                </div>

                <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
                  <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-purple-400" /> Agent Stages
                  </div>
                  <div className="text-lg font-bold text-white mt-1 font-mono">
                    {traceData.tree_nodes?.length || 0}
                  </div>
                </div>

                <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
                  <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" /> Case Status
                  </div>
                  <div className="text-lg font-bold text-cyan-300 mt-1 font-mono">
                    {traceData.status}
                  </div>
                </div>
              </div>

              {/* Tree Structure */}
              <div className="glass-standard rounded-2xl p-5 border border-white/[0.08]">
                <div className="flex items-center gap-2 text-xs font-mono text-slate-400 uppercase tracking-wider mb-4 border-b border-white/[0.06] pb-2">
                  <GitBranch className="w-4 h-4 text-cyan-400" />
                  <span>Case Cognitive Execution Tree — {traceData.case_id}</span>
                </div>

                <div className="space-y-3 font-sans">
                  {traceData.tree_nodes?.map((node: any, idx: number) => {
                    const isExpanded = expandedNodes[node.agent_type] !== false;
                    return (
                      <div
                        key={idx}
                        className="rounded-xl bg-white/[0.02] border border-white/[0.05] p-3.5 hover:border-cyan-500/30 transition-colors"
                      >
                        <div
                          onClick={() => toggleNode(node.agent_type)}
                          className="flex items-center justify-between cursor-pointer select-none"
                        >
                          <div className="flex items-center gap-3">
                            {isExpanded ? (
                              <ChevronDown className="w-4 h-4 text-slate-400" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-slate-400" />
                            )}
                            <div className="w-2 h-2 rounded-full bg-cyan-400" />
                            <span className="text-sm font-semibold text-white">
                              {node.agent_name}
                            </span>
                            <span className="text-[10px] px-2 py-0.5 rounded bg-white/[0.06] text-slate-300 font-mono">
                              {node.agent_type}
                            </span>
                          </div>

                          <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
                            <span className="flex items-center gap-1 text-slate-300">
                              <Clock className="w-3 h-3 text-cyan-400" />
                              {node.latency_ms}ms
                            </span>
                            <span className="flex items-center gap-1 text-emerald-400">
                              <Coins className="w-3 h-3" />
                              ${node.token_usage?.cost_usd?.toFixed(4)}
                            </span>
                            <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                              {node.status}
                            </span>
                          </div>
                        </div>

                        {isExpanded && (
                          <div className="mt-3 pt-3 border-t border-white/[0.04] space-y-2.5 text-xs">
                            {node.output_summary && (
                              <div>
                                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Output Summary:</span>
                                <p className="text-slate-200 mt-0.5 leading-relaxed">{node.output_summary}</p>
                              </div>
                            )}

                            {node.evidence_summary && (
                              <div>
                                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Evidence Grounding (No CoT):</span>
                                <p className="text-slate-300 font-mono text-[11px] bg-black/30 p-2 rounded-lg border border-white/[0.04] mt-0.5">
                                  {node.evidence_summary}
                                </p>
                              </div>
                            )}

                            {/* Nested Tool Calls */}
                            {node.tool_calls && node.tool_calls.length > 0 && (
                              <div className="mt-2 space-y-1.5">
                                <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider flex items-center gap-1">
                                  <Wrench className="w-3 h-3" /> Executed Database Tool Calls ({node.tool_calls.length})
                                </span>
                                {node.tool_calls.map((tool: any, tIdx: number) => (
                                  <div
                                    key={tIdx}
                                    className="bg-cyan-950/20 border border-cyan-500/20 rounded-lg p-2.5 font-mono text-[11px] space-y-1"
                                  >
                                    <div className="flex items-center justify-between text-cyan-300 font-semibold">
                                      <span>🔧 {tool.tool_name}</span>
                                      <span className="text-slate-400">{tool.duration_ms}ms</span>
                                    </div>
                                    <div className="text-slate-400 text-[10px]">
                                      Input: {JSON.stringify(tool.input_params)}
                                    </div>
                                    <div className="text-emerald-400 text-[10px]">
                                      Result: {JSON.stringify(tool.output_result)}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. AGENT PERFORMANCE METRICS */}
      {activeTab === 'agents' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agentMetrics.map((agent, idx) => (
            <div
              key={idx}
              className="glass-card rounded-2xl p-4 border border-white/[0.08] hover:border-cyan-500/30 transition-all space-y-3"
            >
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-cyan-400" />
                  {agent.agent_name}
                </h3>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-mono">
                  {agent.success_rate}% Success
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-white/[0.02] p-2 rounded-lg border border-white/[0.04]">
                  <span className="text-[10px] text-slate-400">Total Runs</span>
                  <div className="text-white font-bold text-sm mt-0.5">{agent.total_runs}</div>
                </div>
                <div className="bg-white/[0.02] p-2 rounded-lg border border-white/[0.04]">
                  <span className="text-[10px] text-slate-400">Avg Latency</span>
                  <div className="text-cyan-300 font-bold text-sm mt-0.5">{agent.avg_latency_ms}ms</div>
                </div>
                <div className="bg-white/[0.02] p-2 rounded-lg border border-white/[0.04]">
                  <span className="text-[10px] text-slate-400">Confidence</span>
                  <div className="text-purple-300 font-bold text-sm mt-0.5">{(agent.avg_confidence * 100).toFixed(0)}%</div>
                </div>
                <div className="bg-white/[0.02] p-2 rounded-lg border border-white/[0.04]">
                  <span className="text-[10px] text-slate-400">Avg Cost</span>
                  <div className="text-emerald-400 font-bold text-sm mt-0.5">${agent.avg_cost_usd?.toFixed(4)}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 3. TOOL PERFORMANCE METRICS */}
      {activeTab === 'tools' && (
        <div className="glass-standard rounded-2xl p-5 border border-white/[0.08] overflow-x-auto">
          <table className="w-full text-left text-xs font-sans">
            <thead>
              <tr className="border-b border-white/[0.08] text-slate-400 font-mono text-[11px] uppercase tracking-wider">
                <th className="pb-3 px-3">Tool Name</th>
                <th className="pb-3 px-3">Invocations</th>
                <th className="pb-3 px-3">Success Rate</th>
                <th className="pb-3 px-3">Avg Latency</th>
                <th className="pb-3 px-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] font-mono">
              {toolMetrics.map((tool, idx) => (
                <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 px-3 font-semibold text-white flex items-center gap-2">
                    <Wrench className="w-3.5 h-3.5 text-cyan-400" />
                    {tool.tool_name}
                  </td>
                  <td className="py-3 px-3 text-slate-300">{tool.total_calls}</td>
                  <td className="py-3 px-3 text-emerald-400 font-bold">{tool.success_rate}%</td>
                  <td className="py-3 px-3 text-slate-300">{tool.avg_duration_ms}ms</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      Operational
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 4. FAILURE ANALYSIS */}
      {activeTab === 'failures' && failureReport && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="glass-card p-4 rounded-xl border border-white/[0.06]">
              <div className="text-xs text-slate-400 font-mono">Total Cases Analyzed</div>
              <div className="text-xl font-bold text-white mt-1">{failureReport.total_cases_analyzed}</div>
            </div>
            <div className="glass-card p-4 rounded-xl border border-white/[0.06]">
              <div className="text-xs text-slate-400 font-mono">Replanning Loops</div>
              <div className="text-xl font-bold text-amber-300 mt-1">{failureReport.replan_loop_count}</div>
            </div>
            <div className="glass-card p-4 rounded-xl border border-white/[0.06]">
              <div className="text-xs text-slate-400 font-mono">Human Escalation Rate</div>
              <div className="text-xl font-bold text-rose-300 mt-1">{failureReport.escalated_cases_count}</div>
            </div>
          </div>

          <div className="glass-standard rounded-2xl p-5 border border-white/[0.08]">
            <h3 className="text-sm font-bold text-white font-mono uppercase tracking-wider mb-3">
              Common System Exception & Escalation Root Causes
            </h3>
            <div className="space-y-2.5">
              {failureReport.common_errors?.map((err: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] flex items-center justify-between text-xs"
                >
                  <div className="space-y-0.5">
                    <div className="font-semibold text-rose-300 font-mono">{err.error_type}</div>
                    <div className="text-slate-400">{err.description}</div>
                  </div>
                  <span className="px-2.5 py-1 rounded-lg bg-rose-500/20 text-rose-300 font-mono font-bold">
                    {err.count} occurrences
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
