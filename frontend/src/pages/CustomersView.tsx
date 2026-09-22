import React, { useState, useEffect } from 'react';
import { 
  Users, 
  Search, 
  Package, 
  Clock, 
  CheckCircle2, 
  Brain, 
  ShieldCheck, 
  ChevronRight, 
  RefreshCw, 
  ExternalLink,
  MessageSquarePlus,
  DollarSign
} from 'lucide-react';
import { getCustomers, getCustomer360 } from '../services/api';
import { Customer, Customer360 } from '../types';
import { useAuth } from '../context/AuthContext';

interface Props {
  onSelectCustomerToChat?: (customer: Customer) => void;
  onCreateCaseForCustomer?: (customerId: string) => void;
}

export const CustomersView: React.FC<Props> = ({ onSelectCustomerToChat, onCreateCaseForCustomer }) => {
  const { user } = useAuth();
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>('CUST1002');
  const [customer360, setCustomer360] = useState<Customer360 | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [tierFilter, setTierFilter] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isDossierLoading, setIsDossierLoading] = useState<boolean>(false);

  const fetchCustomerList = async () => {
    setIsLoading(true);
    try {
      const res = await getCustomers();
      if (res?.customers) {
        setCustomers(res.customers);
      }
    } catch (err) {
      console.error('Failed to load customers:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const loadCustomer360 = async (id: string) => {
    setIsDossierLoading(true);
    setSelectedCustomerId(id);
    try {
      const data = await getCustomer360(id);
      setCustomer360(data);
    } catch (err) {
      console.error('Failed to load customer 360:', err);
    } finally {
      setIsDossierLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomerList();
  }, [user?.organization_id]);

  useEffect(() => {
    if (selectedCustomerId) {
      loadCustomer360(selectedCustomerId);
    }
  }, [selectedCustomerId]);

  const filteredCustomers = customers.filter(c => {
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchName = c.name?.toLowerCase().includes(term);
      const matchId = c.customer_id?.toLowerCase().includes(term);
      const matchEmail = c.email?.toLowerCase().includes(term);
      if (!matchName && !matchId && !matchEmail) return false;
    }
    if (tierFilter !== 'ALL' && c.tier?.toLowerCase() !== tierFilter.toLowerCase()) {
      return false;
    }
    return true;
  });

  const getTierBadge = (tier: string) => {
    switch (tier?.toLowerCase()) {
      case 'platinum':
        return <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">Platinum VIP</span>;
      case 'gold':
        return <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">Gold</span>;
      case 'silver':
        return <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-slate-400/20 text-slate-300 border border-slate-400/30">Silver</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">Standard</span>;
    }
  };

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1700px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-tr from-cyan-600 to-blue-600 rounded-xl shadow-lg shadow-cyan-500/20 text-white">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Customer 360 Intelligence Hub</h1>
              <p className="text-xs text-slate-400 font-mono">
                Unified profiles, loyalty status, order history, and verified customer memory • Tenant: <span className="text-cyan-400 font-semibold">{user?.organization_id}</span>
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchCustomerList}
          className="p-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-xl transition-all self-start sm:self-auto"
          title="Refresh Customers"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Main 2-Column Split: Directory List on Left (5 cols) & Customer 360 Dossier on Right (7 cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left 5 Cols: Searchable Customer Directory */}
        <div className="lg:col-span-5 bg-slate-900/80 border border-slate-800 rounded-2xl p-5 backdrop-blur-md space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-white">Customer Directory</h2>
            <span className="text-xs text-slate-400 font-mono">{filteredCustomers.length} registered</span>
          </div>

          {/* Search & Tier Filter */}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Search name, ID, email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 bg-slate-800 border border-slate-700 rounded-xl text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
              />
            </div>

            <select
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
              className="bg-slate-800 border border-slate-700 rounded-xl px-2.5 py-1.5 text-xs text-cyan-300 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="ALL">All Tiers</option>
              <option value="platinum">Platinum</option>
              <option value="gold">Gold</option>
              <option value="silver">Silver</option>
              <option value="standard">Standard</option>
            </select>
          </div>

          {/* Directory List */}
          <div className="space-y-2 max-h-[640px] overflow-y-auto pr-1">
            {filteredCustomers.map((c) => {
              const isSelected = selectedCustomerId === c.customer_id;
              return (
                <div
                  key={c.customer_id}
                  onClick={() => loadCustomer360(c.customer_id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between ${
                    isSelected
                      ? 'bg-cyan-500/15 border-cyan-500/40 shadow-lg shadow-cyan-500/10'
                      : 'bg-slate-800/40 border-slate-700/50 hover:bg-slate-800/80'
                  }`}
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-xs truncate">{c.name}</span>
                      {getTierBadge(c.tier)}
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono truncate">{c.email}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{c.customer_id}</div>
                  </div>

                  <ChevronRight className={`w-4 h-4 transition-transform ${isSelected ? 'text-cyan-400 translate-x-1' : 'text-slate-500'}`} />
                </div>
              );
            })}
          </div>
        </div>

        {/* Right 7 Cols: Full Customer 360 Profile Dossier */}
        <div className="lg:col-span-7 space-y-5">
          {isDossierLoading ? (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-16 text-center text-slate-400 text-xs">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-cyan-400" />
              Assembling 360 intelligence dossier...
            </div>
          ) : customer360 ? (
            <>
              {/* Profile Card */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <h2 className="text-xl font-bold text-white">{customer360.profile.name}</h2>
                      {getTierBadge(customer360.loyalty.tier)}
                    </div>
                    <div className="text-xs text-slate-400 font-mono">
                      {customer360.profile.customer_id} • {customer360.profile.email} • {customer360.profile.phone || 'No phone on file'}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {onSelectCustomerToChat && (
                      <button
                        onClick={() => {
                          const c = customers.find(x => x.customer_id === selectedCustomerId);
                          if (c) onSelectCustomerToChat(c);
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-xl text-xs font-semibold transition-all"
                      >
                        <MessageSquarePlus className="w-3.5 h-3.5" /> Start Chat
                      </button>
                    )}
                  </div>
                </div>

                {/* Loyalty & Spend Statistics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800">
                  <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/40">
                    <div className="text-[10px] text-slate-400 uppercase font-medium">Lifetime Spend</div>
                    <div className="text-base font-extrabold text-emerald-400 font-mono">
                      ${customer360.loyalty.lifetime_spend.toFixed(2)}
                    </div>
                  </div>

                  <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/40">
                    <div className="text-[10px] text-slate-400 uppercase font-medium">Orders Count</div>
                    <div className="text-base font-extrabold text-white">
                      {customer360.loyalty.order_count}
                    </div>
                  </div>

                  <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/40">
                    <div className="text-[10px] text-slate-400 uppercase font-medium">Account Status</div>
                    <div className="text-base font-extrabold text-cyan-400">
                      {customer360.profile.account_status}
                    </div>
                  </div>

                  <div className="bg-slate-800/40 p-3 rounded-xl border border-slate-700/40">
                    <div className="text-[10px] text-slate-400 uppercase font-medium">Active Cases</div>
                    <div className="text-base font-extrabold text-amber-400">
                      {customer360.cases.filter(c => !['RESOLVED', 'CLOSED'].includes(c.status)).length}
                    </div>
                  </div>
                </div>
              </div>

              {/* Order History with Carrier Tracking */}
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Package className="w-4 h-4 text-purple-400" />
                  Order History & Real-Time Tracking
                </h3>

                <div className="space-y-3">
                  {customer360.orders.map((ord: any) => (
                    <div key={ord.order_id} className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-700/50 space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-cyan-300">{ord.order_id}</span>
                          <span className="text-slate-400 font-mono">${ord.total_amount.toFixed(2)}</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                          ord.status === 'Delayed' ? 'bg-amber-500/20 text-amber-300' :
                          ord.status === 'Refunded' ? 'bg-purple-500/20 text-purple-300' :
                          ord.status === 'Delivered' ? 'bg-emerald-500/20 text-emerald-300' :
                          'bg-slate-700 text-slate-300'
                        }`}>
                          {ord.status}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1 border-t border-slate-700/40 font-mono">
                        <span>Carrier: <strong className="text-slate-200">{ord.carrier || 'Standard'}</strong></span>
                        <span>Tracking: <strong className="text-cyan-400">{ord.tracking_number || 'N/A'}</strong></span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Verified Memory Facts */}
              {customer360.memories && customer360.memories.length > 0 && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-4">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Brain className="w-4 h-4 text-cyan-400" />
                    Long-Term Customer Memories & Context
                  </h3>

                  <div className="space-y-2">
                    {customer360.memories.map((m: any, idx: number) => (
                      <div key={idx} className="p-3 rounded-xl bg-slate-800/40 border-l-4 border-cyan-500 text-xs text-slate-200 leading-relaxed">
                        {m.value}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-16 text-center text-slate-500 text-xs">
              Select a customer from the directory to inspect 360 intelligence.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
