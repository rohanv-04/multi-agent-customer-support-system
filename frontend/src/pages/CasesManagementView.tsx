import React, { useState, useEffect } from 'react';
import { 
  Layers, 
  Search, 
  Filter, 
  Plus, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  RefreshCw, 
  ArrowUpDown, 
  UserCheck, 
  ChevronRight,
  Sparkles,
  MessageSquare
} from 'lucide-react';
import { getCases, createCase } from '../services/api';
import { useAuth } from '../context/AuthContext';

interface Props {
  onSelectCase: (caseId: string) => void;
  initialFilter?: string;
}

export const CasesManagementView: React.FC<Props> = ({ onSelectCase, initialFilter }) => {
  const { user } = useAuth();
  const [cases, setCases] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  
  // Filter states
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>(initialFilter === 'active' ? 'ACTIVE' : (initialFilter || 'ALL'));
  const [priorityFilter, setPriorityFilter] = useState<string>('ALL');
  const [channelFilter, setChannelFilter] = useState<string>('ALL');
  const [slaFilter, setSlaFilter] = useState<string>(initialFilter === 'sla_risk' ? 'RISK' : 'ALL');

  // Create Case Modal state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [newSubject, setNewSubject] = useState<string>('');
  const [newDescription, setNewDescription] = useState<string>('');
  const [newCustomerId, setNewCustomerId] = useState<string>('CUST1002');
  const [newPriority, setNewPriority] = useState<string>('medium');
  const [newChannel, setNewChannel] = useState<string>('web_chat');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const fetchCases = async () => {
    setIsLoading(true);
    try {
      const data = await getCases();
      setCases(data || []);
    } catch (err) {
      console.error('Failed to load cases:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [user?.organization_id]);

  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      const created = await createCase({
        customer_id: newCustomerId,
        subject: newSubject,
        description: newDescription,
        priority: newPriority,
        channel: newChannel,
        initial_message: newDescription,
        organization_id: user?.organization_id
      });
      setShowCreateModal(false);
      setNewSubject('');
      setNewDescription('');
      fetchCases();
      if (created?.id) {
        onSelectCase(created.id);
      }
    } catch (err) {
      console.error('Failed to create case:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const now = new Date();

  // Filter application
  const filteredCases = cases.filter((c) => {
    // Search
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const matchSubject = c.subject?.toLowerCase().includes(term);
      const matchId = c.id?.toLowerCase().includes(term);
      const matchCust = c.customer_id?.toLowerCase().includes(term);
      const matchIntent = c.intent?.toLowerCase().includes(term);
      if (!matchSubject && !matchId && !matchCust && !matchIntent) return false;
    }

    // Status
    if (statusFilter === 'ACTIVE') {
      if (['RESOLVED', 'CLOSED'].includes(c.status)) return false;
    } else if (statusFilter !== 'ALL') {
      if (c.status !== statusFilter) return false;
    }

    // Priority
    if (priorityFilter !== 'ALL') {
      if (c.priority?.toLowerCase() !== priorityFilter.toLowerCase()) return false;
    }

    // Channel
    if (channelFilter !== 'ALL') {
      if (c.channel !== channelFilter) return false;
    }

    // SLA Risk
    if (slaFilter === 'RISK') {
      if (['RESOLVED', 'CLOSED'].includes(c.status)) return false;
      if (!c.sla_deadline) return false;
      const isBreached = new Date(c.sla_deadline) < now;
      const diffMin = (new Date(c.sla_deadline).getTime() - now.getTime()) / (1000 * 60);
      const isDueSoon = diffMin >= 0 && diffMin <= 60;
      if (!isBreached && !isDueSoon) return false;
    }

    return true;
  });

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1700px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-tr from-cyan-600 to-blue-600 rounded-xl shadow-lg shadow-cyan-500/20 text-white">
              <Layers className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Support Case Operations</h1>
              <p className="text-xs text-slate-400 font-mono">
                {filteredCases.length} of {cases.length} cases filtered • Tenant: <span className="text-cyan-400 font-semibold">{user?.organization_id}</span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchCases}
            className="p-2.5 bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 rounded-xl transition-all"
            title="Refresh Queue"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2.5 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs shadow-lg shadow-cyan-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            Create Support Case
          </button>
        </div>
      </div>

      {/* Multi-Dimensional Filter Toolbar */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-4 backdrop-blur-md flex flex-wrap items-center gap-3">
        {/* Search */}
        <div className="relative flex-1 min-w-[240px]">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by case ID, subject, customer, intent..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800/80 border border-slate-700/80 rounded-xl text-xs text-white placeholder-slate-400 focus:outline-none focus:border-cyan-500"
          />
        </div>

        {/* Status Filter */}
        <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 rounded-xl px-3 py-1.5">
          <span className="text-[11px] text-slate-400 font-medium">Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-transparent text-xs text-cyan-300 font-semibold focus:outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-slate-900 text-white">All Statuses</option>
            <option value="ACTIVE" className="bg-slate-900 text-white">Active Only</option>
            <option value="NEW" className="bg-slate-900 text-white">NEW</option>
            <option value="TRIAGING" className="bg-slate-900 text-white">TRIAGING</option>
            <option value="INVESTIGATING" className="bg-slate-900 text-white">INVESTIGATING</option>
            <option value="DECISION_PENDING" className="bg-slate-900 text-white">DECISION PENDING</option>
            <option value="ACTION_PENDING" className="bg-slate-900 text-white">ACTION PENDING</option>
            <option value="VERIFYING" className="bg-slate-900 text-white">VERIFYING</option>
            <option value="RESOLVED" className="bg-slate-900 text-white">RESOLVED</option>
            <option value="ESCALATED" className="bg-slate-900 text-white">ESCALATED</option>
            <option value="CLOSED" className="bg-slate-900 text-white">CLOSED</option>
          </select>
        </div>

        {/* Priority Filter */}
        <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 rounded-xl px-3 py-1.5">
          <span className="text-[11px] text-slate-400 font-medium">Priority:</span>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-transparent text-xs text-slate-200 font-semibold focus:outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-slate-900 text-white">All Priorities</option>
            <option value="urgent" className="bg-slate-900 text-red-400">Urgent</option>
            <option value="high" className="bg-slate-900 text-amber-400">High</option>
            <option value="medium" className="bg-slate-900 text-blue-400">Medium</option>
            <option value="low" className="bg-slate-900 text-slate-400">Low</option>
          </select>
        </div>

        {/* Channel Filter */}
        <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 rounded-xl px-3 py-1.5">
          <span className="text-[11px] text-slate-400 font-medium">Channel:</span>
          <select
            value={channelFilter}
            onChange={(e) => setChannelFilter(e.target.value)}
            className="bg-transparent text-xs text-slate-200 font-semibold focus:outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-slate-900 text-white">All Channels</option>
            <option value="web_chat" className="bg-slate-900 text-white">Web Chat</option>
            <option value="email" className="bg-slate-900 text-white">Email</option>
            <option value="whatsapp" className="bg-slate-900 text-white">WhatsApp</option>
            <option value="api" className="bg-slate-900 text-white">API</option>
            <option value="portal" className="bg-slate-900 text-white">Support Form</option>
          </select>
        </div>

        {/* SLA Status Filter */}
        <div className="flex items-center gap-1.5 bg-slate-800/80 border border-slate-700/80 rounded-xl px-3 py-1.5">
          <span className="text-[11px] text-slate-400 font-medium">SLA Risk:</span>
          <select
            value={slaFilter}
            onChange={(e) => setSlaFilter(e.target.value)}
            className="bg-transparent text-xs text-amber-400 font-semibold focus:outline-none cursor-pointer"
          >
            <option value="ALL" className="bg-slate-900 text-white">All SLAs</option>
            <option value="RISK" className="bg-slate-900 text-red-400">At Risk / Breached</option>
          </select>
        </div>
      </div>

      {/* Enterprise Cases Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-md">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-800/30 text-xs font-semibold text-slate-400">
                <th className="py-3.5 px-4">Case ID</th>
                <th className="py-3.5 px-4">Subject & Intent</th>
                <th className="py-3.5 px-4">Customer</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Priority</th>
                <th className="py-3.5 px-4">Channel</th>
                <th className="py-3.5 px-4">SLA Deadline</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredCases.map((c) => {
                const isBreached = c.sla_deadline && new Date(c.sla_deadline) < now && !['RESOLVED', 'CLOSED'].includes(c.status);
                return (
                  <tr 
                    key={c.id} 
                    onClick={() => onSelectCase(c.id)}
                    className="hover:bg-slate-800/40 cursor-pointer transition-colors group"
                  >
                    <td className="py-3.5 px-4 font-mono font-bold text-cyan-400 text-xs">
                      {c.id}
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-white group-hover:text-cyan-300 transition-colors">{c.subject}</div>
                      <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                        <span className="font-mono text-[11px] text-slate-500">{c.intent || 'General Support'}</span>
                        {c.sentiment && (
                          <span className={`px-1.5 py-0.2 rounded text-[10px] font-semibold ${
                            c.sentiment === 'frustrated' ? 'text-red-400 bg-red-500/10' :
                            c.sentiment === 'negative' ? 'text-amber-400 bg-amber-500/10' :
                            'text-slate-400 bg-slate-800'
                          }`}>
                            {c.sentiment}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="text-xs font-medium text-slate-300">{c.customer_id}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
                        c.status === 'RESOLVED' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' :
                        c.status === 'ESCALATED' ? 'bg-red-500/15 text-red-400 border-red-500/30' :
                        c.status === 'INVESTIGATING' ? 'bg-blue-500/15 text-blue-400 border-blue-500/30' :
                        c.status === 'ACTION_PENDING' ? 'bg-purple-500/15 text-purple-400 border-purple-500/30' :
                        'bg-amber-500/15 text-amber-400 border-amber-500/30'
                      }`}>
                        {c.status}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`text-xs font-bold ${
                        c.priority === 'urgent' ? 'text-red-400' :
                        c.priority === 'high' ? 'text-amber-400' :
                        c.priority === 'medium' ? 'text-blue-400' :
                        'text-slate-400'
                      }`}>
                        {c.priority?.toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-300 capitalize">
                      {c.channel || 'web_chat'}
                    </td>
                    <td className="py-3.5 px-4 text-xs">
                      {isBreached ? (
                        <span className="inline-flex items-center gap-1.5 text-red-400 font-bold font-mono">
                          <AlertTriangle className="w-3.5 h-3.5" /> BREACHED
                        </span>
                      ) : c.sla_deadline ? (
                        <span className="inline-flex items-center gap-1.5 text-slate-300 font-mono">
                          <Clock className="w-3.5 h-3.5 text-slate-400" />
                          {new Date(c.sla_deadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-cyan-300 rounded-lg text-xs font-semibold inline-flex items-center gap-1 transition-all">
                        Workspace <ChevronRight className="w-3 h-3" />
                      </button>
                    </td>
                  </tr>
                );
              })}

              {filteredCases.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400 text-sm">
                    No cases match the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Case Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <Plus className="w-5 h-5 text-cyan-400" />
              Register Support Case
            </h3>

            <form onSubmit={handleCreateCase} className="space-y-4">
              <div>
                <label className="text-xs text-slate-400 font-medium">Customer ID</label>
                <input
                  type="text"
                  required
                  value={newCustomerId}
                  onChange={(e) => setNewCustomerId(e.target.value)}
                  placeholder="e.g. CUST1002"
                  className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-medium">Subject</label>
                <input
                  type="text"
                  required
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  placeholder="e.g. Package ORD10002 severely delayed"
                  className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400 font-medium">Description / Initial Inbound Message</label>
                <textarea
                  required
                  rows={3}
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="Describe the issue or paste customer's message..."
                  className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400 font-medium">Priority</label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}
                    className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-slate-400 font-medium">Channel</label>
                  <select
                    value={newChannel}
                    onChange={(e) => setNewChannel(e.target.value)}
                    className="w-full mt-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-500"
                  >
                    <option value="web_chat">Web Chat</option>
                    <option value="email">Email</option>
                    <option value="whatsapp">WhatsApp</option>
                    <option value="api">API</option>
                    <option value="portal">Support Form</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold rounded-xl text-xs shadow-lg shadow-cyan-600/20 disabled:opacity-50"
                >
                  {isSubmitting ? 'Registering...' : 'Create & Triage'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
