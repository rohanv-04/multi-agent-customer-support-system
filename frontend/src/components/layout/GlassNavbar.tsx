import React from 'react';
import { Bot, Sparkles, ShieldCheck, Users, Activity } from 'lucide-react';
import { Customer } from '../../types';

interface Props {
  currentCustomer: Customer | null;
  customers: Customer[];
  onSelectCustomer: (cust: Customer) => void;
  systemStatus: string;
}

export const GlassNavbar: React.FC<Props> = ({
  currentCustomer,
  customers,
  onSelectCustomer,
  systemStatus
}) => {
  return (
    <header className="sticky top-4 z-40 px-4 sm:px-6">
      <div className="glass-floating rounded-2xl px-5 py-3 flex items-center justify-between transition-all duration-300">
        {/* Left: Brand Identity */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-blue-600/30 border border-cyan-400/30 shadow-glow-cyan">
            <Bot className="w-5 h-5 text-cyan-300" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full ring-2 ring-charcoal-950 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-semibold tracking-wide text-white">AgentSupport AI</h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                NovaCart
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">Autonomous Multi-Agent Platform</p>
          </div>
        </div>

        {/* Center: Real Operational Health */}
        <div className="hidden md:flex items-center gap-6">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.08]">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-xs text-slate-300 font-medium">{systemStatus}</span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.08]">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-xs text-slate-300 font-mono">7 Agents Online</span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.03] border border-white/[0.08]">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-xs text-slate-300 font-mono">LangGraph Orchestrated</span>
          </div>
        </div>

        {/* Right: Customer Demo Switcher */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/[0.04] border border-white/[0.1]">
            <Users className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs text-slate-400 hidden sm:inline">Active Customer:</span>
            <select
              value={currentCustomer?.customer_id || ''}
              onChange={(e) => {
                const found = customers.find(c => c.customer_id === e.target.value);
                if (found) onSelectCustomer(found);
              }}
              className="bg-transparent text-xs text-cyan-300 font-medium focus:outline-none cursor-pointer pr-2"
            >
              {customers.map((c) => (
                <option key={c.customer_id} value={c.customer_id} className="bg-charcoal-900 text-slate-200">
                  {c.name} ({c.customer_id} - {c.tier})
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
