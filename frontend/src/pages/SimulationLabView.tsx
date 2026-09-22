import React, { useState, useEffect } from 'react';
import {
  FlaskConical,
  Play,
  ShieldCheck,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Cpu,
  Lock,
  Boxes,
  Layers,
  ArrowRight,
  Fingerprint,
  Zap,
  Activity
} from 'lucide-react';
import { getSimulationScenarios, runSimulation } from '../services/api';
import { SimulationScenario, SimulationRunResult } from '../types';

export const SimulationLabView: React.FC = () => {
  const [scenarios, setScenarios] = useState<SimulationScenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<SimulationScenario | null>(null);
  const [issueDescription, setIssueDescription] = useState<string>('');
  const [carrierApiDown, setCarrierApiDown] = useState<boolean>(true);
  const [refundLimit, setRefundLimit] = useState<number>(500);
  const [unsupportedPolicy, setUnsupportedPolicy] = useState<boolean>(false);
  const [running, setRunning] = useState<boolean>(false);
  const [runResult, setRunResult] = useState<SimulationRunResult | null>(null);

  useEffect(() => {
    loadScenarios();
  }, []);

  const loadScenarios = async () => {
    try {
      const data = await getSimulationScenarios();
      if (Array.isArray(data) && data.length > 0) {
        setScenarios(data);
        handleSelectScenario(data[0]);
      }
    } catch (e) {
      console.error('Failed to load scenarios:', e);
    }
  };

  const handleSelectScenario = (scen: SimulationScenario) => {
    setSelectedScenario(scen);
    setIssueDescription(scen.issue_description);
    setCarrierApiDown(Boolean(scen.system_conditions?.carrier_api_down));
    setUnsupportedPolicy(Boolean(scen.system_conditions?.unsupported_policy));
    setRefundLimit(scen.system_conditions?.refund_limit || 500);
    setRunResult(null);
  };

  const handleExecuteSimulation = async () => {
    if (!issueDescription.trim()) return;
    setRunning(true);
    setRunResult(null);
    try {
      const res = await runSimulation({
        scenario_id: selectedScenario?.id,
        customer_id: selectedScenario?.customer_profile?.customer_id || 'CUST1002',
        issue_description: issueDescription,
        system_conditions: {
          carrier_api_down: carrierApiDown,
          unsupported_policy: unsupportedPolicy,
          refund_limit: refundLimit
        }
      });
      setRunResult(res);
    } catch (err) {
      console.error('Simulation execution failed:', err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-6 rounded-2xl border border-slate-800">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-500/20 to-cyan-500/20 border border-indigo-500/30">
              <FlaskConical className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
                AI Simulation Lab
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 font-mono">
                  Sandbox Workbench
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Safely stress-test multi-agent workflows, chaos conditions, and guardrail policies with 0 real business mutations.
              </p>
            </div>
          </div>
        </div>

        {/* Safety Badge */}
        <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold self-start">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>STRICT SAFETY ISOLATION: ACTIVE</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Scenario Configurator */}
        <div className="lg:col-span-4 space-y-4">
          <div className="glass-card p-5 rounded-2xl border border-slate-800 space-y-4">
            <h2 className="text-sm font-semibold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" />
              Pre-Configured Scenarios
            </h2>

            <div className="space-y-2">
              {scenarios.map((scen) => (
                <button
                  key={scen.id}
                  onClick={() => handleSelectScenario(scen)}
                  className={`w-full text-left p-3 rounded-xl border transition-all ${
                    selectedScenario?.id === scen.id
                      ? 'bg-indigo-500/15 border-indigo-500/50 text-slate-100'
                      : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                  }`}
                >
                  <div className="text-xs font-semibold text-slate-200">{scen.name}</div>
                  <div className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">{scen.description}</div>
                </button>
              ))}
            </div>

            <div className="pt-3 border-t border-slate-800 space-y-3">
              <label className="text-xs font-medium text-slate-300 block">Simulated Customer Goal / Prompt</label>
              <textarea
                rows={3}
                value={issueDescription}
                onChange={(e) => setIssueDescription(e.target.value)}
                className="w-full text-xs p-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-100 focus:outline-none focus:border-indigo-500 font-mono resize-none"
                placeholder="Enter customer support inquiry to simulate..."
              />
            </div>

            {/* Chaos & System Conditions */}
            <div className="pt-3 border-t border-slate-800 space-y-2.5">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
                Chaos Injections & Limits
              </span>

              <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={carrierApiDown}
                  onChange={(e) => setCarrierApiDown(e.target.checked)}
                  className="rounded border-slate-700 text-indigo-500 focus:ring-0"
                />
                Simulate Carrier Tracking API Failure
              </label>

              <label className="flex items-center gap-2.5 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={unsupportedPolicy}
                  onChange={(e) => setUnsupportedPolicy(e.target.checked)}
                  className="rounded border-slate-700 text-indigo-500 focus:ring-0"
                />
                Simulate Policy Ambiguity / Crypto Request
              </label>

              <div className="pt-2">
                <div className="flex justify-between text-xs text-slate-400 mb-1">
                  <span>Auto-Approval Max Cap</span>
                  <span className="font-mono text-indigo-400">${refundLimit} USD</span>
                </div>
                <input
                  type="range"
                  min={100}
                  max={1500}
                  step={50}
                  value={refundLimit}
                  onChange={(e) => setRefundLimit(Number(e.target.value))}
                  className="w-full accent-indigo-500"
                />
              </div>
            </div>

            <button
              onClick={handleExecuteSimulation}
              disabled={running}
              className="w-full py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 disabled:opacity-50 transition-all"
            >
              {running ? (
                <>
                  <Activity className="w-4 h-4 animate-spin text-slate-950" />
                  Running Sandboxed Simulation...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current text-slate-950" />
                  Run Multi-Agent Simulation
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Execution Workbench & Trace */}
        <div className="lg:col-span-8 space-y-4">
          {runResult ? (
            <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-6">
              {/* Simulation Result Header */}
              <div className="flex items-center justify-between pb-4 border-b border-slate-800">
                <div className="flex items-center gap-2.5">
                  <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                      Simulation Run: {runResult.run_id}
                      <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                        {runResult.total_duration_ms}ms
                      </span>
                    </h2>
                    <span className="text-xs text-slate-400">
                      Multi-agent graph completed in sandboxed isolation mode.
                    </span>
                  </div>
                </div>

                <div className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-mono font-semibold">
                  Zero Real DB Writes
                </div>
              </div>

              {/* Diagnostic Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800 text-xs space-y-1">
                  <span className="text-slate-400 uppercase font-medium text-[10px] tracking-wider block">
                    Synthesized Case DNA
                  </span>
                  <div className="font-bold text-slate-200">
                    {runResult.case_dna?.severity?.toUpperCase() || 'HIGH'} • {runResult.case_dna?.affected_business_area?.toUpperCase() || 'LOGISTICS'}
                  </div>
                  <div className="text-[11px] text-indigo-400 font-mono">
                    {runResult.case_dna?.required_capabilities?.length || 4} capabilities
                  </div>
                </div>

                <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800 text-xs space-y-1">
                  <span className="text-slate-400 uppercase font-medium text-[10px] tracking-wider block">
                    Customer Friction
                  </span>
                  <div className="font-bold text-slate-200">
                    Score {runResult.friction_profile?.score || 45.0} • {runResult.friction_profile?.level || 'MEDIUM'}
                  </div>
                  <div className="text-[11px] text-amber-400 font-mono">
                    {runResult.friction_profile?.recent_trend || 'stable'} trend
                  </div>
                </div>

                <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800 text-xs space-y-1">
                  <span className="text-slate-400 uppercase font-medium text-[10px] tracking-wider block">
                    Action Outcome
                  </span>
                  <div className="font-bold text-slate-200 uppercase">
                    {runResult.final_outcome?.decision || 'DECISION_PENDING'}
                  </div>
                  <div className="text-[11px] text-cyan-400 font-mono">
                    Approval: {runResult.final_outcome?.requires_human_approval ? 'Required' : 'Auto-Approved'}
                  </div>
                </div>
              </div>

              {/* Sandboxed Tool Invocations */}
              <div className="space-y-2">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  Simulated Swarm Tool Invocations ({runResult.simulated_tool_calls?.length || 0})
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {runResult.simulated_tool_calls?.map((t, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-slate-900/50 border border-slate-800 text-xs space-y-1 font-mono"
                    >
                      <div className="flex justify-between items-center text-slate-200">
                        <span>{t.tool}</span>
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded ${
                            t.status.includes('error') ? 'bg-red-500/20 text-red-400' : 'bg-emerald-500/20 text-emerald-400'
                          }`}
                        >
                          {t.status}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400">Duration: {t.duration_ms}ms</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Step-by-Step Execution Trace */}
              <div className="space-y-2">
                <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                  <Activity className="w-4 h-4 text-cyan-400" />
                  Multi-Agent Execution Spans ({runResult.execution_trace?.length || 0})
                </h3>

                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {runResult.execution_trace?.map((ev, i) => (
                    <div
                      key={i}
                      className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between text-slate-300">
                        <span className="font-semibold text-indigo-400">{ev.agent}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 font-mono text-slate-400">
                          {ev.phase}
                        </span>
                      </div>
                      <p className="text-slate-200 text-xs">{ev.action}</p>
                      {ev.details && (
                        <pre className="text-[10px] text-slate-400 font-mono p-2 rounded bg-slate-900 overflow-x-auto">
                          {JSON.stringify(ev.details, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-card p-16 rounded-2xl border border-slate-800 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center mx-auto">
                <FlaskConical className="w-6 h-6 text-indigo-400" />
              </div>
              <h3 className="text-base font-bold text-slate-100">Simulation Lab Ready</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                Configure chaos parameters and test prompts on the left, then click &quot;Run Multi-Agent Simulation&quot; to inspect real-time agent decisions.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default SimulationLabView;
