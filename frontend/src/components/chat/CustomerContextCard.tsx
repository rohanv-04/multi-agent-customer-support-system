import React, { useState, useEffect } from 'react';
import {
  User,
  Package,
  Clock,
  Shield,
  Brain,
  CreditCard,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  FileText,
  Activity,
  Layers
} from 'lucide-react';
import { Customer, Customer360 } from '../../types';
import { getCustomer360 } from '../../services/api';

interface Props {
  customer: Customer | null;
  activeCaseId?: string | null;
  caseStatus?: string;
  casePriority?: string;
  sentiment?: string;
}

export const CustomerContextCard: React.FC<Props> = ({
  customer,
  activeCaseId,
  caseStatus = 'INVESTIGATING',
  casePriority = 'high',
  sentiment = 'frustrated'
}) => {
  const [c360, setC360] = useState<Customer360 | null>(null);
  const [activeTab, setActiveTab] = useState<'360' | 'orders' | 'cases' | 'memory'>('360');
  const [loading, setLoading] = useState<boolean>(false);

  useEffect(() => {
    if (customer?.customer_id) {
      setLoading(true);
      getCustomer360(customer.customer_id)
        .then((data) => setC360(data))
        .catch((err) => console.error('Failed to load Customer 360:', err))
        .finally(() => setLoading(false));
    }
  }, [customer?.customer_id]);

  if (!customer) {
    return (
      <div className="glass-standard rounded-2xl p-4 text-center text-slate-400 text-xs">
        No customer profile selected.
      </div>
    );
  }

  const getTierColor = (tier: string) => {
    switch (tier?.toLowerCase()) {
      case 'platinum':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-400/40';
      case 'gold':
        return 'bg-amber-500/20 text-amber-300 border-amber-400/40';
      case 'silver':
        return 'bg-slate-300/20 text-slate-200 border-slate-300/40';
      default:
        return 'bg-white/10 text-slate-300 border-white/20';
    }
  };

  const getRiskColor = (risk: string) => {
    switch (risk?.toUpperCase()) {
      case 'HIGH':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse';
      case 'MEDIUM':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      default:
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40';
    }
  };

  const getOrderStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'refunded':
      case 'delivered':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'delayed':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40 animate-pulse';
      case 'shipped':
        return 'bg-blue-500/15 text-blue-300 border-blue-500/30';
      case 'cancelled':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      default:
        return 'bg-slate-500/15 text-slate-300 border-slate-500/30';
    }
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Active Case Context Capsule */}
      {activeCaseId && (
        <div className="glass-standard rounded-2xl p-3.5 border border-cyan-500/30 bg-gradient-to-r from-cyan-950/40 to-slate-900/60 shadow-glow-cyan">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] uppercase font-mono font-bold tracking-wider text-cyan-400 flex items-center gap-1.5">
              <Activity className="w-3 h-3 text-cyan-400 animate-spin" /> Active SupportCase
            </span>
            <span className="px-2 py-0.5 rounded-full text-[9px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
              {caseStatus}
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-white">
            <span className="font-mono font-bold text-cyan-200">{activeCaseId}</span>
            <div className="flex items-center gap-2 text-[10px]">
              <span className="text-slate-300 font-mono capitalize">Priority: <strong className="text-amber-400">{casePriority}</strong></span>
              <span className="text-slate-300 font-mono capitalize">Sentiment: <strong className="text-rose-400">{sentiment}</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* Customer 360 Main Dossier */}
      <div className="glass-standard rounded-2xl p-4 flex flex-col gap-3.5">
        {/* Header Profile & Loyalty */}
        <div className="flex items-start justify-between border-b border-white/[0.08] pb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500/30 to-violet-600/30 border border-white/20 flex items-center justify-center font-bold text-cyan-200 text-sm">
              {customer.name.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-semibold text-white">{customer.name}</h4>
                <span className="text-[9px] font-mono text-cyan-400 bg-cyan-500/10 px-1.5 py-0.2 rounded border border-cyan-500/20">
                  {customer.customer_id}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-mono">{customer.email}</p>
            </div>
          </div>

          <div className="flex flex-col items-end gap-1">
            <span className={`px-2 py-0.5 rounded-full text-[9px] font-semibold border ${getTierColor(customer.tier)}`}>
              {customer.tier} Tier
            </span>
            {c360?.risk_assessment && (
              <span className={`px-2 py-0.5 rounded-full text-[8px] font-bold uppercase border ${getRiskColor(c360.risk_assessment.risk_level)}`}>
                Risk: {c360.risk_assessment.risk_level}
              </span>
            )}
          </div>
        </div>

        {/* Customer 360 KPIs */}
        {c360 && (
          <div className="grid grid-cols-3 gap-2 text-center bg-white/[0.02] p-2 rounded-xl border border-white/[0.05]">
            <div className="p-1">
              <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Spend</span>
              <span className="text-xs font-bold text-emerald-400">${c360.loyalty.lifetime_spend.toFixed(0)}</span>
            </div>
            <div className="p-1 border-x border-white/[0.08]">
              <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Orders</span>
              <span className="text-xs font-bold text-cyan-300">{c360.loyalty.order_count}</span>
            </div>
            <div className="p-1">
              <span className="text-[9px] text-slate-400 uppercase tracking-wider block">Open Cases</span>
              <span className="text-xs font-bold text-amber-300">{c360.open_cases_count}</span>
            </div>
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex rounded-lg bg-black/20 p-1 text-[11px] border border-white/[0.06]">
          <button
            onClick={() => setActiveTab('360')}
            className={`flex-1 py-1 rounded-md transition-all font-medium ${activeTab === '360' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-white'}`}
          >
            360 Intel
          </button>
          <button
            onClick={() => setActiveTab('orders')}
            className={`flex-1 py-1 rounded-md transition-all font-medium ${activeTab === 'orders' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-white'}`}
          >
            Orders ({c360?.orders?.length || customer.orders?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('cases')}
            className={`flex-1 py-1 rounded-md transition-all font-medium ${activeTab === 'cases' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-white'}`}
          >
            History
          </button>
          <button
            onClick={() => setActiveTab('memory')}
            className={`flex-1 py-1 rounded-md transition-all font-medium ${activeTab === 'memory' ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400 hover:text-white'}`}
          >
            Memory
          </button>
        </div>

        {/* TAB 1: Customer 360 Intelligence Overview */}
        {activeTab === '360' && (
          <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1 text-xs">
            {c360?.risk_assessment?.churn_signals && c360.risk_assessment.churn_signals.length > 0 && (
              <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-[11px]">
                <div className="flex items-center gap-1.5 font-bold mb-1 text-amber-300 text-[10px] uppercase">
                  <AlertTriangle className="w-3 h-3" /> Churn Risk Indicators
                </div>
                <ul className="list-disc pl-3.5 space-y-0.5 text-[10px] text-amber-200/90">
                  {c360.risk_assessment.churn_signals.map((sig, idx) => (
                    <li key={idx}>{sig}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Loyalty Perks */}
            {c360?.loyalty?.perks && c360.loyalty.perks.length > 0 && (
              <div>
                <span className="text-[10px] uppercase tracking-wider font-semibold text-slate-400 block mb-1">
                  Active Tier Privileges
                </span>
                <div className="space-y-1">
                  {c360.loyalty.perks.map((perk, idx) => (
                    <div key={idx} className="flex items-center gap-1.5 text-[10px] text-cyan-200 bg-cyan-500/5 p-1 rounded border border-cyan-500/10">
                      <CheckCircle2 className="w-3 h-3 text-cyan-400 shrink-0" />
                      <span>{perk}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: Orders & Payments */}
        {activeTab === 'orders' && (
          <div className="space-y-2 max-h-60 overflow-y-auto pr-1 text-xs">
            {(c360?.orders || customer.orders || []).map((ord) => (
              <div
                key={ord.order_id}
                className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.07] hover:border-white/20 transition-all"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono font-bold text-white text-[11px]">{ord.order_id}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[9px] font-semibold border ${getOrderStatusColor(ord.status)}`}>
                    {ord.status}
                  </span>
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-300">
                  <span>Total: <strong className="text-emerald-400">${ord.total_amount?.toFixed(2)}</strong></span>
                  {ord.carrier && (
                    <span className="text-[10px] text-slate-400 font-mono">{ord.carrier} ({ord.tracking_number})</span>
                  )}
                </div>

                {ord.delay_reason && (
                  <div className="mt-1 text-[10px] text-amber-300/90 bg-amber-500/10 p-1.5 rounded border border-amber-500/20">
                    {ord.delay_reason}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* TAB 3: History (Cases, Complaints, Resolutions) */}
        {activeTab === 'cases' && (
          <div className="space-y-2 max-h-60 overflow-y-auto pr-1 text-xs">
            {c360?.previous_complaints && c360.previous_complaints.length > 0 && (
              <div>
                <span className="text-[10px] uppercase tracking-wider font-semibold text-rose-400 block mb-1">
                  Previous Complaints ({c360.previous_complaints.length})
                </span>
                <div className="space-y-1">
                  {c360.previous_complaints.map((c, idx) => (
                    <div key={idx} className="p-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-[10px]">
                      <span className="font-mono font-bold text-rose-300 block">{c.complaint_id} ({c.severity})</span>
                      <p className="text-slate-300">{c.issue}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {c360?.previous_resolutions && c360.previous_resolutions.length > 0 && (
              <div className="mt-2">
                <span className="text-[10px] uppercase tracking-wider font-semibold text-emerald-400 block mb-1">
                  Previous Resolutions ({c360.previous_resolutions.length})
                </span>
                <div className="space-y-1">
                  {c360.previous_resolutions.map((r, idx) => (
                    <div key={idx} className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[10px]">
                      <span className="font-mono font-bold text-emerald-300 block">{r.resolution_id}</span>
                      <p className="text-slate-300">{r.outcome_summary}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: Persistent Memory */}
        {activeTab === 'memory' && (
          <div className="space-y-1.5 max-h-60 overflow-y-auto text-[11px]">
            {(!c360?.memories || c360.memories.length === 0) ? (
              <p className="text-slate-400 text-[10px] italic">No custom preferences logged yet.</p>
            ) : (
              c360.memories.map((m, idx) => (
                <div key={idx} className="p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                  <span className="text-[9px] font-mono uppercase text-violet-400 block">{m.key}</span>
                  <p className="text-slate-300 text-[10px] leading-tight">{m.value}</p>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
};
