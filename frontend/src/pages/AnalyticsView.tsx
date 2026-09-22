import React from 'react';
import { BarChart3, TrendingUp, CheckCircle, AlertTriangle, Wrench, RefreshCw } from 'lucide-react';
import { AnalyticsData } from '../types';

interface Props {
  analytics: AnalyticsData | null;
}

export const AnalyticsView: React.FC<Props> = ({ analytics }) => {
  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-10">
      <div className="glass-elevated rounded-3xl p-6 sm:p-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 rounded-2xl bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 shadow-glow-cyan">
            <BarChart3 className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">System Performance & Analytics</h2>
            <p className="text-xs text-slate-400 font-mono">
              Empirical metrics on task resolution rates, tool execution frequencies, & re-planning events
            </p>
          </div>
        </div>
      </div>

      {/* Metrics Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-standard p-5 rounded-2xl">
          <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Total Task Volume</span>
          <div className="text-2xl font-bold text-white font-mono">{analytics?.total_tasks || 0}</div>
          <span className="text-xs text-slate-400 mt-1 block">Live LangGraph Runs</span>
        </div>

        <div className="glass-standard p-5 rounded-2xl">
          <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Resolution Rate</span>
          <div className="text-2xl font-bold text-emerald-400 font-mono">{analytics?.resolution_rate || 100}%</div>
          <span className="text-xs text-slate-400 mt-1 block">Autonomous Closure</span>
        </div>

        <div className="glass-standard p-5 rounded-2xl">
          <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Tool Success Rate</span>
          <div className="text-2xl font-bold text-cyan-400 font-mono">{analytics?.tool_success_rate || 100}%</div>
          <span className="text-xs text-slate-400 mt-1 block">{analytics?.total_tool_calls || 0} Operations</span>
        </div>

        <div className="glass-standard p-5 rounded-2xl">
          <span className="text-[10px] font-mono uppercase text-slate-400 block mb-1">Re-Planning Events</span>
          <div className="text-2xl font-bold text-amber-400 font-mono">{analytics?.total_replanning_events || 0}</div>
          <span className="text-xs text-slate-400 mt-1 block">Loops Executed</span>
        </div>
      </div>

      {/* Tool Distribution Breakdown */}
      <div className="glass-standard rounded-2xl p-6">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
          <Wrench className="w-4 h-4 text-cyan-400" />
          <span>Tool Execution Breakdown</span>
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {Object.entries(analytics?.tool_distribution || {}).map(([tool, count]) => (
            <div key={tool} className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <span className="font-mono text-xs text-cyan-300 font-bold block mb-1">{tool}</span>
              <div className="text-xl font-bold text-white font-mono">{count}</div>
              <span className="text-[10px] text-slate-400 font-mono">Invocations</span>
            </div>
          ))}
          {Object.keys(analytics?.tool_distribution || {}).length === 0 && (
            <p className="text-xs text-slate-400 italic">No tool calls logged yet.</p>
          )}
        </div>
      </div>
    </div>
  );
};
