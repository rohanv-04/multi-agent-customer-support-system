import React, { useState, useEffect } from 'react';
import {
  Network,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingUp,
  FileText,
  Boxes,
  Truck,
  CreditCard,
  Layers,
  Sparkles,
  Search,
  ExternalLink
} from 'lucide-react';
import { getRootCauses } from '../services/api';
import { RootCauseItem } from '../types';

export const RootCausesView: React.FC = () => {
  const [rootCauses, setRootCauses] = useState<RootCauseItem[]>([]);
  const [selectedRC, setSelectedRC] = useState<RootCauseItem | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [filterCategory, setFilterCategory] = useState<string>('all');

  useEffect(() => {
    fetchRootCauses();
  }, []);

  const fetchRootCauses = async () => {
    setLoading(true);
    try {
      const data = await getRootCauses();
      if (Array.isArray(data)) {
        setRootCauses(data);
        if (data.length > 0 && !selectedRC) {
          setSelectedRC(data[0]);
        }
      }
    } catch (e) {
      console.error('Failed to load root causes:', e);
    } finally {
      setLoading(false);
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'carrier':
      case 'logistics':
        return <Truck className="w-5 h-5 text-amber-400" />;
      case 'product':
      case 'hardware':
        return <Boxes className="w-5 h-5 text-indigo-400" />;
      case 'payment':
      case 'billing':
        return <CreditCard className="w-5 h-5 text-emerald-400" />;
      default:
        return <Layers className="w-5 h-5 text-cyan-400" />;
    }
  };

  const filteredCauses = rootCauses.filter((rc) =>
    filterCategory === 'all' ? true : rc.category.toLowerCase() === filterCategory.toLowerCase()
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-card p-6 rounded-2xl border border-slate-800">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30">
              <Network className="w-6 h-6 text-amber-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
                Root Cause Intelligence
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono">
                  Systemic Detection
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Autonomous clustering of cross-case telemetry to isolate systemic business bottlenecks.
              </p>
            </div>
          </div>
        </div>

        {/* Category Filters */}
        <div className="flex items-center gap-2 bg-slate-900/60 p-1.5 rounded-xl border border-slate-800 self-start">
          {['all', 'carrier', 'product', 'payment'].map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${
                filterCategory === cat
                  ? 'bg-amber-500 text-slate-950 font-semibold shadow-md'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Grid Content */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Root Cause Clusters List */}
        <div className="lg:col-span-5 space-y-3">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1">
            Active Systemic Clusters ({filteredCauses.length})
          </div>

          {loading ? (
            <div className="glass-card p-8 rounded-xl border border-slate-800 text-center text-slate-400 text-sm">
              Analyzing support telemetry and clustering issues...
            </div>
          ) : filteredCauses.length === 0 ? (
            <div className="glass-card p-8 rounded-xl border border-slate-800 text-center text-slate-400 text-sm">
              No root causes detected in this category.
            </div>
          ) : (
            filteredCauses.map((rc) => {
              const isSelected = selectedRC?.id === rc.id;
              const isConfirmed = rc.status === 'CONFIRMED_ROOT_CAUSE';

              return (
                <div
                  key={rc.id}
                  onClick={() => setSelectedRC(rc)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all duration-200 ${
                    isSelected
                      ? 'bg-slate-800/80 border-amber-500/50 shadow-lg shadow-amber-500/5'
                      : 'glass-card border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2.5">
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                        {getCategoryIcon(rc.category)}
                      </div>
                      <div>
                        <span className="text-[11px] font-mono font-medium text-slate-400 block uppercase">
                          {rc.id} • {rc.category}
                        </span>
                        <h3 className="text-sm font-semibold text-slate-100 line-clamp-1">{rc.title}</h3>
                      </div>
                    </div>

                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full font-semibold shrink-0 uppercase tracking-wider ${
                        isConfirmed
                          ? 'bg-red-500/10 border border-red-500/30 text-red-400'
                          : 'bg-amber-500/10 border border-amber-500/30 text-amber-400'
                      }`}
                    >
                      {isConfirmed ? 'Confirmed Root Cause' : 'Detected Pattern'}
                    </span>
                  </div>

                  <p className="text-xs text-slate-400 line-clamp-2 mb-3">{rc.description}</p>

                  <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/60 font-mono">
                    <div className="flex items-center gap-3">
                      <span>{rc.affected_cases_count} Cases</span>
                      <span>•</span>
                      <span>{rc.affected_customers_count} Customers</span>
                    </div>
                    <div className="flex items-center gap-1 text-amber-400 font-semibold">
                      <span>{(rc.confidence * 100).toFixed(0)}% Confidence</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Detailed Evidence & Affected Cases Dossier */}
        <div className="lg:col-span-7">
          {selectedRC ? (
            <div className="glass-card p-6 rounded-2xl border border-slate-800 space-y-6">
              {/* Detail Header */}
              <div className="flex items-start justify-between gap-4 pb-4 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      {selectedRC.id}
                    </span>
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase ${
                        selectedRC.status === 'CONFIRMED_ROOT_CAUSE'
                          ? 'bg-red-500/20 text-red-300 border border-red-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {selectedRC.status.replace('_', ' ')}
                    </span>
                  </div>
                  <h2 className="text-lg font-bold text-slate-100">{selectedRC.title}</h2>
                  <p className="text-xs text-slate-400 mt-1">{selectedRC.description}</p>
                </div>
              </div>

              {/* Metrics Ribbon */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80">
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">
                    Affected Cases
                  </span>
                  <div className="text-xl font-bold text-slate-100">{selectedRC.affected_cases_count}</div>
                  <span className="text-[10px] text-slate-400">Linked support tickets</span>
                </div>

                <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80">
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">
                    Affected Accounts
                  </span>
                  <div className="text-xl font-bold text-slate-100">{selectedRC.affected_customers_count}</div>
                  <span className="text-[10px] text-slate-400">Impacted customers</span>
                </div>

                <div className="bg-slate-900/60 p-3.5 rounded-xl border border-slate-800/80">
                  <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider block mb-1">
                    Evidence Confidence
                  </span>
                  <div className="text-xl font-bold text-amber-400">
                    {(selectedRC.confidence * 100).toFixed(0)}%
                  </div>
                  <span className="text-[10px] text-slate-400">Telemetry correlation</span>
                </div>
              </div>

              {/* Telemetry Evidence Section */}
              <div className="space-y-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  <FileText className="w-4 h-4 text-amber-400" />
                  Correlated Telemetry Evidence ({selectedRC.evidence.length})
                </div>

                <div className="space-y-2">
                  {selectedRC.evidence.map((ev, i) => (
                    <div
                      key={i}
                      className="p-3.5 rounded-xl bg-slate-900/40 border border-slate-800 text-xs space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-amber-400 font-semibold uppercase text-[11px]">
                          Evidence #{i + 1} • {ev.evidence_type}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                          {(ev.confidence * 100).toFixed(0)}% Conf.
                        </span>
                      </div>
                      <p className="text-slate-300">{ev.description}</p>
                      {ev.raw_data && (
                        <pre className="p-2 rounded bg-slate-950/80 text-[10px] font-mono text-emerald-400 overflow-x-auto border border-slate-800/60">
                          {JSON.stringify(ev.raw_data, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-card p-12 rounded-2xl border border-slate-800 text-center text-slate-400 text-sm">
              Select a root cause from the left to view deep telemetry and linked cases.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
export default RootCausesView;
