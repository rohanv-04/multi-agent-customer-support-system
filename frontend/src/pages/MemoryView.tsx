import React, { useState, useEffect } from 'react';
import { Brain, Plus, User, Package, Calendar, Tag } from 'lucide-react';
import { Customer } from '../types';
import { getCustomerMemory, saveCustomerMemory } from '../services/api';

interface Props {
  currentCustomer: Customer | null;
}

export const MemoryView: React.FC<Props> = ({ currentCustomer }) => {
  const [memoryContext, setMemoryContext] = useState<any | null>(null);
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');
  const [newType, setNewType] = useState('preference');
  const [saving, setSaving] = useState(false);

  const fetchMemory = async () => {
    if (!currentCustomer) return;
    try {
      const data = await getCustomerMemory(currentCustomer.customer_id);
      setMemoryContext(data);
    } catch (e) {
      console.error('Error fetching customer memory:', e);
    }
  };

  useEffect(() => {
    fetchMemory();
  }, [currentCustomer]);

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey.trim() || !newValue.trim() || !currentCustomer) return;
    setSaving(true);
    try {
      await saveCustomerMemory(currentCustomer.customer_id, newKey, newValue, newType);
      setNewKey('');
      setNewValue('');
      await fetchMemory();
    } catch (err) {
      console.error('Error saving memory:', err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-10">
      <div className="glass-elevated rounded-3xl p-6 sm:p-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-violet-500/20 border border-violet-500/30 text-violet-300 shadow-glow-cyan">
            <Brain className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Persistent Memory Explorer</h2>
            <p className="text-xs text-slate-400 font-mono">
              Long-term profile recall, persistent interaction history, & customer preferences
            </p>
          </div>
        </div>

        <span className="px-3 py-1 rounded-full text-xs font-mono font-medium bg-violet-500/20 text-violet-300 border border-violet-500/30">
          Target: {currentCustomer?.name} ({currentCustomer?.customer_id})
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Customer Profile & Past Orders (1 col) */}
        <div className="glass-standard rounded-2xl p-5 space-y-4">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <User className="w-3.5 h-3.5 text-cyan-400" />
            <span>Profile Overview</span>
          </h3>

          <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06] space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Name:</span>
              <span className="font-semibold text-white">{currentCustomer?.name}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Customer ID:</span>
              <span className="font-mono text-cyan-300">{currentCustomer?.customer_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Loyalty Tier:</span>
              <span className="text-amber-300 font-semibold">{currentCustomer?.tier}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Account Status:</span>
              <span className="text-emerald-400 font-semibold">{currentCustomer?.account_status}</span>
            </div>
          </div>

          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5 pt-2">
            <Package className="w-3.5 h-3.5 text-emerald-400" />
            <span>Recorded Orders</span>
          </h3>

          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {memoryContext?.orders?.map((ord: any) => (
              <div key={ord.order_id} className="p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.05] text-xs">
                <div className="flex justify-between font-mono mb-1">
                  <span className="font-bold text-white">{ord.order_id}</span>
                  <span className="text-cyan-300">{ord.status}</span>
                </div>
                <div className="text-[11px] text-slate-400">
                  Total: <span className="text-emerald-400 font-semibold">${ord.total_amount?.toFixed(2)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Stored Context Memories (2 cols) */}
        <div className="lg:col-span-2 space-y-5">
          {/* Add New Memory Entry Form */}
          <div className="glass-standard rounded-2xl p-5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-1.5">
              <Plus className="w-3.5 h-3.5 text-cyan-400" />
              <span>Record New Memory Fact</span>
            </h3>

            <form onSubmit={handleAddMemory} className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <input
                type="text"
                placeholder="Key (e.g. preferred_shipping)"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                className="px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.1] text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-400"
              />
              <input
                type="text"
                placeholder="Value (e.g. Always requests FedEx delivery)"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                className="px-3 py-2 rounded-xl bg-white/[0.04] border border-white/[0.1] text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-400"
              />
              <button
                type="submit"
                disabled={saving || !newKey || !newValue}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-violet-600 to-cyan-500 text-white text-xs font-medium hover:opacity-90 disabled:opacity-40 transition-all shadow-glow-cyan"
              >
                {saving ? 'Saving...' : 'Persist to SQLite'}
              </button>
            </form>
          </div>

          {/* Stored Facts Cards */}
          <div className="glass-standard rounded-2xl p-5">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-1.5">
              <Brain className="w-3.5 h-3.5 text-violet-400" />
              <span>Active Customer Memory Ledger ({memoryContext?.memories?.length || 0})</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {memoryContext?.memories?.map((m: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.07] hover:border-violet-400/30 transition-all space-y-1 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase font-bold text-violet-300">{m.key}</span>
                    <span className="px-2 py-0.2 rounded text-[9px] font-mono bg-white/[0.05] text-slate-400">
                      {m.type}
                    </span>
                  </div>
                  <p className="text-slate-200 text-xs leading-relaxed font-sans">{m.value}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
