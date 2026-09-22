import React, { useState, useEffect } from 'react';
import {
  Shield,
  Search,
  Filter,
  RefreshCw,
  User,
  Clock,
  FileText,
  CheckCircle2,
  AlertCircle,
  Eye,
  X
} from 'lucide-react';
import { getAuditLogs } from '../services/api';

export function AuditLogExplorerView() {
  const [logs, setLogs] = useState<any[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [actorTypeFilter, setActorTypeFilter] = useState('');
  const [loading, setLoading] = useState(false);
  const [selectedLog, setSelectedLog] = useState<any | null>(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const data = await getAuditLogs({
        search: searchQuery || undefined,
        entity_type: entityFilter || undefined,
        actor_type: actorTypeFilter || undefined,
        limit: 100
      });
      setLogs(data.logs || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [entityFilter, actorTypeFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass-standard rounded-2xl p-5 border border-white/[0.08] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-xs uppercase tracking-wider mb-1">
            <Shield className="w-4 h-4" />
            <span>Immutable Enterprise Ledger</span>
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">
            Audit Log Explorer (5W1H Traceability)
          </h1>
          <p className="text-slate-400 text-xs">
            Guaranteed traceability for every sensitive autonomous decision: Who, What, When, Why, and Result.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="px-4 py-2 rounded-xl bg-white/[0.06] hover:bg-white/[0.1] text-xs text-white font-mono flex items-center gap-2 border border-white/[0.1] transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          Refresh Ledger
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="glass-card rounded-2xl p-4 border border-white/[0.06] flex flex-col sm:flex-row items-center gap-3">
        <div className="flex-1 flex items-center gap-2 bg-white/[0.03] px-3 py-2 rounded-xl border border-white/[0.06] w-full">
          <Search className="w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && fetchLogs()}
            placeholder="Search action, actor, entity ID, or reason..."
            className="bg-transparent text-xs text-white placeholder-slate-500 focus:outline-none flex-1 font-mono"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <select
            value={entityFilter}
            onChange={(e) => setEntityFilter(e.target.value)}
            className="px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs text-white focus:outline-none font-mono"
          >
            <option value="" className="bg-slate-900">All Entities</option>
            <option value="SupportCase" className="bg-slate-900">SupportCase</option>
            <option value="Refund" className="bg-slate-900">Refund</option>
            <option value="AgentAction" className="bg-slate-900">AgentAction</option>
            <option value="EscalationTicket" className="bg-slate-900">EscalationTicket</option>
          </select>

          <select
            value={actorTypeFilter}
            onChange={(e) => setActorTypeFilter(e.target.value)}
            className="px-3 py-2 rounded-xl bg-white/[0.03] border border-white/[0.06] text-xs text-white focus:outline-none font-mono"
          >
            <option value="" className="bg-slate-900">All Actors</option>
            <option value="agent" className="bg-slate-900">Agent</option>
            <option value="system" className="bg-slate-900">System</option>
            <option value="user" className="bg-slate-900">Human User</option>
          </select>

          <button
            onClick={fetchLogs}
            className="px-4 py-2 rounded-xl bg-cyan-500 text-slate-950 font-bold text-xs hover:bg-cyan-400 transition-colors shadow-glow-cyan"
          >
            Search
          </button>
        </div>
      </div>

      {/* Audit Logs Table */}
      <div className="glass-standard rounded-2xl p-5 border border-white/[0.08] overflow-x-auto">
        <table className="w-full text-left text-xs font-sans">
          <thead>
            <tr className="border-b border-white/[0.08] text-slate-400 font-mono text-[11px] uppercase tracking-wider">
              <th className="pb-3 px-3">When</th>
              <th className="pb-3 px-3">Who (Actor)</th>
              <th className="pb-3 px-3">What (Action)</th>
              <th className="pb-3 px-3">Target Entity</th>
              <th className="pb-3 px-3">Why (Justification)</th>
              <th className="pb-3 px-3">Result</th>
              <th className="pb-3 px-3 text-right">Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04]">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-white/[0.02] transition-colors">
                <td className="py-3 px-3 font-mono text-slate-400 text-[11px]">
                  {new Date(log.when).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </td>
                <td className="py-3 px-3 font-semibold text-cyan-300">
                  {log.who}
                </td>
                <td className="py-3 px-3 font-mono text-white font-semibold">
                  {log.what}
                </td>
                <td className="py-3 px-3 font-mono text-slate-300">
                  <span className="px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06] text-[10px]">
                    {log.entity_type} #{log.entity_id}
                  </span>
                </td>
                <td className="py-3 px-3 text-slate-300 max-w-xs truncate">
                  {log.why}
                </td>
                <td className="py-3 px-3 font-mono">
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    {log.result}
                  </span>
                </td>
                <td className="py-3 px-3 text-right">
                  <button
                    onClick={() => setSelectedLog(log)}
                    className="p-1.5 rounded-lg bg-white/[0.04] hover:bg-white/[0.1] text-slate-300 hover:text-white transition-colors"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {logs.length === 0 && !loading && (
          <div className="py-12 text-center text-slate-500 text-xs font-mono">
            No audit records match the specified query filters.
          </div>
        )}
      </div>

      {/* Detail Drawer Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="glass-modal rounded-2xl p-6 max-w-2xl w-full border border-white/[0.1] space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2 text-cyan-300 font-mono text-sm font-bold">
                <Shield className="w-4 h-4" />
                Audit Record #{selectedLog.id}
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="p-1 rounded-lg hover:bg-white/[0.06] text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                <span className="text-[10px] text-slate-500">Actor (Who)</span>
                <div className="text-white font-bold mt-0.5">{selectedLog.who}</div>
              </div>
              <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                <span className="text-[10px] text-slate-500">Action (What)</span>
                <div className="text-cyan-300 font-bold mt-0.5">{selectedLog.what}</div>
              </div>
              <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                <span className="text-[10px] text-slate-500">Target Entity</span>
                <div className="text-white font-bold mt-0.5">{selectedLog.entity_type} ({selectedLog.entity_id})</div>
              </div>
              <div className="bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                <span className="text-[10px] text-slate-500">Timestamp (When)</span>
                <div className="text-slate-300 font-bold mt-0.5">{new Date(selectedLog.when).toLocaleString()}</div>
              </div>
            </div>

            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Justification (Why):</span>
              <p className="text-xs text-slate-200 mt-1 bg-white/[0.02] p-2.5 rounded-xl border border-white/[0.04]">
                {selectedLog.why}
              </p>
            </div>

            <div>
              <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">Payload & Cryptographic Audit Diff:</span>
              <pre className="text-[11px] font-mono text-emerald-400 bg-black/40 p-3 rounded-xl border border-white/[0.06] mt-1 overflow-x-auto max-h-48">
                {JSON.stringify(selectedLog.details, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
