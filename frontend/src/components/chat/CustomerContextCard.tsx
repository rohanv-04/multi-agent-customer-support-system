import React from 'react';
import { User, Package, Clock, Shield, Brain, CreditCard, ExternalLink } from 'lucide-react';
import { Customer } from '../../types';

interface Props {
  customer: Customer | null;
  memories?: any[];
}

export const CustomerContextCard: React.FC<Props> = ({ customer, memories = [] }) => {
  if (!customer) {
    return (
      <div className="glass-standard rounded-2xl p-4 text-center text-slate-400 text-xs">
        No customer profile selected.
      </div>
    );
  }

  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
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

  const getOrderStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
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
    <div className="glass-standard rounded-2xl p-4 flex flex-col gap-4">
      {/* Header Profile */}
      <div className="flex items-start justify-between border-b border-white/[0.08] pb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500/30 to-violet-600/30 border border-white/20 flex items-center justify-center font-bold text-cyan-200">
            {customer.name.charAt(0)}
          </div>
          <div>
            <h4 className="text-sm font-semibold text-white">{customer.name}</h4>
            <p className="text-[11px] text-slate-400 font-mono">{customer.email}</p>
          </div>
        </div>

        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${getTierColor(customer.tier)}`}>
          {customer.tier} Tier
        </span>
      </div>

      {/* Orders Section */}
      <div>
        <div className="flex items-center gap-2 mb-2">
          <Package className="w-3.5 h-3.5 text-cyan-400" />
          <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Order Portfolio ({customer.orders?.length || 0})
          </h5>
        </div>

        <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
          {customer.orders?.map((ord) => (
            <div
              key={ord.order_id}
              className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.07] hover:border-white/20 transition-all text-xs"
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
                  <span className="text-[10px] text-slate-400 font-mono">{ord.carrier}</span>
                )}
              </div>

              {ord.delay_reason && (
                <div className="mt-1 text-[10px] text-amber-300/90 bg-amber-500/10 p-1 rounded border border-amber-500/20">
                  {ord.delay_reason}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Persistent Customer Memory */}
      <div className="border-t border-white/[0.08] pt-3">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="w-3.5 h-3.5 text-violet-400" />
          <h5 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
            Persistent Context & Memory
          </h5>
        </div>

        <div className="space-y-1.5 max-h-36 overflow-y-auto text-[11px]">
          {memories.length === 0 ? (
            <p className="text-slate-400 text-[10px] italic">No custom memories logged yet.</p>
          ) : (
            memories.map((m, idx) => (
              <div key={idx} className="p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.05]">
                <span className="text-[9px] font-mono uppercase text-violet-400 block">{m.key}</span>
                <p className="text-slate-300 text-[10px] leading-tight">{m.value}</p>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
