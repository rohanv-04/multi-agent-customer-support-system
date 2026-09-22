import React, { useState, useEffect } from 'react';
import {
  FlaskConical,
  Play,
  CheckCircle2,
  XCircle,
  Clock,
  Coins,
  ShieldAlert,
  Sliders,
  Filter,
  BarChart2,
  Sparkles,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { getBenchmarks, runEvaluationSuite, getEvaluationRuns } from '../services/api';

const CATEGORIES = [
  { id: 'all', label: 'All Benchmarks' },
  { id: 'delivery_issues', label: 'Delivery Issues' },
  { id: 'refunds', label: 'Refunds' },
  { id: 'cancellations', label: 'Cancellations' },
  { id: 'billing', label: 'Billing' },
  { id: 'policy_questions', label: 'Policy Questions' },
  { id: 'escalation', label: 'Escalation' },
  { id: 'tool_failures', label: 'Tool Failures' },
  { id: 'ambiguous_requests', label: 'Ambiguous Requests' },
];

export function EvaluationLabView() {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [benchmarks, setBenchmarks] = useState<any[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [currentRun, setCurrentRun] = useState<any | null>(null);
  const [runHistory, setRunHistory] = useState<any[]>([]);
  const [expandedCase, setExpandedCase] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [bData, rData] = await Promise.all([
        getBenchmarks(selectedCategory === 'all' ? undefined : selectedCategory),
        getEvaluationRuns()
      ]);
      setBenchmarks(bData);
      setRunHistory(rData);
      if (!currentRun && rData.length > 0) {
        setCurrentRun(rData[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedCategory]);

  const handleRunEvaluation = async () => {
    setIsRunning(true);
    try {
      const categoriesToRun = selectedCategory === 'all' ? undefined : [selectedCategory];
      const result = await runEvaluationSuite(categoriesToRun, undefined, `Suite Run (${selectedCategory})`);
      setCurrentRun(result);
      setRunHistory(prev => [result, ...prev]);
    } catch (e) {
      console.error(e);
    } finally {
      setIsRunning(false);
    }
  };

  const metrics = currentRun?.metrics;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-standard rounded-2xl p-5 border border-white/[0.08] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs uppercase tracking-wider mb-1">
            <FlaskConical className="w-4 h-4" />
            <span>SupportOS AI Evaluation Lab</span>
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            Autonomous Agent Benchmark & Regression Suite
          </h1>
          <p className="text-slate-400 text-xs">
            Evaluates multidimensional intent, policy, decision, tool accuracy, hallucination rates, and cost telemetry.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-cyan-500"
          >
            {CATEGORIES.map(c => (
              <option key={c.id} value={c.id} className="bg-slate-900 text-white">
                {c.label}
              </option>
            ))}
          </select>

          <button
            onClick={handleRunEvaluation}
            disabled={isRunning}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-bold text-xs flex items-center gap-2 shadow-glow-cyan transition-all disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${isRunning ? 'animate-spin' : ''}`} />
            {isRunning ? 'Running Benchmark...' : 'Run Evaluation Suite'}
          </button>
        </div>
      </div>

      {/* 9 ACCURACY METRIC SCORECARDS */}
      {metrics && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Overall Pass Rate</div>
            <div className="text-xl font-bold text-cyan-400 font-mono mt-1">
              {currentRun.pass_rate}%
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">{currentRun.passed_cases}/{currentRun.total_cases} Passed</div>
          </div>

          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Intent Accuracy</div>
            <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
              {metrics.intent_accuracy}%
            </div>
          </div>

          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Policy Accuracy</div>
            <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
              {metrics.policy_accuracy}%
            </div>
          </div>

          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Decision Accuracy</div>
            <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
              {metrics.decision_accuracy}%
            </div>
          </div>

          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Tool Execution</div>
            <div className="text-xl font-bold text-purple-300 font-mono mt-1">
              {metrics.tool_execution_accuracy}%
            </div>
          </div>

          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Verification Acc.</div>
            <div className="text-xl font-bold text-blue-300 font-mono mt-1">
              {metrics.verification_accuracy}%
            </div>
          </div>

          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Escalation Acc.</div>
            <div className="text-xl font-bold text-amber-300 font-mono mt-1">
              {metrics.escalation_accuracy}%
            </div>
          </div>

          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Hallucination Rate</div>
            <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
              {metrics.hallucination_rate}%
            </div>
          </div>

          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Avg Latency</div>
            <div className="text-xl font-bold text-slate-200 font-mono mt-1">
              {metrics.avg_latency_ms} <span className="text-xs text-slate-400">ms</span>
            </div>
          </div>

          <div className="glass-card p-3.5 rounded-xl border border-white/[0.06]">
            <div className="text-[10px] text-slate-400 font-mono uppercase">Total Run Cost</div>
            <div className="text-xl font-bold text-emerald-400 font-mono mt-1">
              ${metrics.total_cost_usd?.toFixed(4)}
            </div>
          </div>
        </div>
      )}

      {/* TEST CASE RESULTS TABLE */}
      {currentRun && (
        <div className="glass-standard rounded-2xl p-5 border border-white/[0.08]">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-xs font-mono text-slate-400 uppercase tracking-wider">
              <BarChart2 className="w-4 h-4 text-cyan-400" />
              <span>Benchmark Case Breakdown — {currentRun.name}</span>
            </div>
            <span className="text-xs text-slate-400 font-mono">{currentRun.cases?.length} Test Cases Evaluated</span>
          </div>

          <div className="space-y-3 font-sans">
            {currentRun.cases?.map((c: any, idx: number) => {
              const isExpanded = expandedCase === c.benchmark_id;
              return (
                <div
                  key={idx}
                  className={`rounded-xl border p-3.5 transition-all ${
                    c.is_passed
                      ? 'bg-emerald-500/[0.02] border-emerald-500/20 hover:border-emerald-500/40'
                      : 'bg-rose-500/[0.02] border-rose-500/20 hover:border-rose-500/40'
                  }`}
                >
                  <div
                    onClick={() => setExpandedCase(isExpanded ? null : c.benchmark_id)}
                    className="flex items-center justify-between cursor-pointer select-none"
                  >
                    <div className="flex items-center gap-3">
                      {c.is_passed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                      )}
                      <div>
                        <span className="text-xs font-mono text-slate-400 mr-2">[{c.benchmark_id}]</span>
                        <span className="text-sm font-semibold text-white">{c.user_goal}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 text-xs font-mono">
                      <span className="px-2 py-0.5 rounded bg-white/[0.06] text-slate-300">
                        {c.category}
                      </span>
                      <span className="text-cyan-400">{c.latency_ms}ms</span>
                      <span className="px-2 py-0.5 rounded-full font-bold text-[10px] bg-cyan-500/20 text-cyan-300">
                        {(c.score * 100).toFixed(0)}% Score
                      </span>
                      {isExpanded ? <ChevronDown className="w-4 h-4 text-slate-400" /> : <ChevronRight className="w-4 h-4 text-slate-400" />}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-white/[0.04] grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono">
                      <div className="bg-black/30 p-2.5 rounded-lg border border-white/[0.04] space-y-1">
                        <div className="text-[10px] text-slate-500 uppercase tracking-wider">Expected Ground Truth:</div>
                        <div><span className="text-slate-400">Intent:</span> <span className="text-white">{c.expected_intent}</span></div>
                        <div><span className="text-slate-400">Decision:</span> <span className="text-white">{c.expected_decision}</span></div>
                        <div><span className="text-slate-400">Policy:</span> <span className="text-white">{c.expected_policy || 'None'}</span></div>
                        <div><span className="text-slate-400">Escalate:</span> <span className="text-white">{c.expected_escalation ? 'Yes' : 'No'}</span></div>
                      </div>

                      <div className="bg-black/30 p-2.5 rounded-lg border border-white/[0.04] space-y-1">
                        <div className="text-[10px] text-cyan-400 uppercase tracking-wider">Actual Agent Evaluation:</div>
                        <div><span className="text-slate-400">Intent:</span> <span className={c.intent_match ? 'text-emerald-400' : 'text-rose-400'}>{c.actual_intent}</span></div>
                        <div><span className="text-slate-400">Decision:</span> <span className={c.decision_match ? 'text-emerald-400' : 'text-rose-400'}>{c.actual_decision}</span></div>
                        <div><span className="text-slate-400">Policy:</span> <span className={c.policy_match ? 'text-emerald-400' : 'text-rose-400'}>{c.actual_policy || 'None'}</span></div>
                        <div><span className="text-slate-400">Escalate:</span> <span className={c.escalation_match ? 'text-emerald-400' : 'text-rose-400'}>{c.actual_escalation ? 'Yes' : 'No'}</span></div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
