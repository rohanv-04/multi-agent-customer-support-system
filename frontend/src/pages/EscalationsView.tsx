import React, { useState, useEffect } from 'react';
import { UserCheck, AlertTriangle, CheckCircle, Clock, ChevronRight, User, Wrench, ShieldAlert } from 'lucide-react';
import { getEscalations, updateEscalationStatus } from '../services/api';

export const EscalationsView: React.FC = () => {
  const [tickets, setTickets] = useState<any[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchTickets = async () => {
    try {
      const data = await getEscalations();
      setTickets(data.tickets || []);
      if (data.tickets && data.tickets.length > 0 && !selectedTicket) {
        setSelectedTicket(data.tickets[0]);
      }
    } catch (e) {
      console.error('Error fetching escalations:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const handleStatusChange = async (ticketId: string, newStatus: string) => {
    try {
      await updateEscalationStatus(ticketId, newStatus, 'Human Specialist #1');
      await fetchTickets();
      if (selectedTicket && selectedTicket.ticket_id === ticketId) {
        setSelectedTicket({ ...selectedTicket, status: newStatus });
      }
    } catch (e) {
      console.error('Error updating status:', e);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'resolved':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      case 'in_progress':
        return 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30 animate-pulse';
      case 'open':
      default:
        return 'bg-rose-500/20 text-rose-300 border-rose-500/30';
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      <div className="glass-elevated rounded-3xl p-6 sm:p-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-rose-500/20 border border-rose-500/30 text-rose-300 shadow-glow-rose">
            <UserCheck className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Human Escalation Desk</h2>
            <p className="text-xs text-slate-400 font-mono">
              Prioritized Handoff Dossiers, Tool Audit Trails & Action Recommendations
            </p>
          </div>
        </div>

        <span className="px-3 py-1 rounded-full text-xs font-mono font-medium bg-rose-500/15 text-rose-300 border border-rose-500/30">
          {tickets.filter(t => t.status === 'open').length} Open Tickets
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Ticket List (5 cols) */}
        <div className="lg:col-span-5 space-y-2.5 max-h-[calc(100vh-16rem)] overflow-y-auto pr-1">
          {tickets.length === 0 ? (
            <div className="glass-standard rounded-2xl p-8 text-center text-xs text-slate-400">
              No escalation tickets recorded in system.
            </div>
          ) : (
            tickets.map((t) => {
              const isSelected = selectedTicket?.ticket_id === t.ticket_id;
              return (
                <div
                  key={t.ticket_id}
                  onClick={() => setSelectedTicket(t)}
                  className={`glass-standard p-4 rounded-2xl cursor-pointer transition-all ${
                    isSelected
                      ? 'border-rose-400/50 bg-rose-500/10 shadow-glow-rose'
                      : 'hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-[11px] font-bold text-rose-300">{t.ticket_id}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-semibold border ${getStatusBadge(t.status)}`}>
                      {t.status.toUpperCase()}
                    </span>
                  </div>

                  <p className="text-xs font-medium text-white line-clamp-2 mb-2">{t.summary}</p>

                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                    <span>Customer: {t.customer_id}</span>
                    <span>Priority: {t.priority?.toUpperCase()}</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Selected Dossier (7 cols) */}
        <div className="lg:col-span-7">
          {selectedTicket ? (
            <div className="glass-standard rounded-2xl p-6 space-y-5">
              {/* Header & Status Switcher */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.08] pb-4">
                <div>
                  <span className="text-[10px] font-mono text-rose-400 uppercase tracking-wider block mb-1">
                    Handoff Dossier: {selectedTicket.ticket_id}
                  </span>
                  <h3 className="text-lg font-bold text-white leading-snug">
                    {selectedTicket.summary}
                  </h3>
                </div>

                <div className="flex items-center gap-1.5 p-1 rounded-xl bg-white/[0.03] border border-white/[0.08]">
                  {(['open', 'in_progress', 'resolved'] as const).map((st) => (
                    <button
                      key={st}
                      onClick={() => handleStatusChange(selectedTicket.ticket_id, st)}
                      className={`px-3 py-1 rounded-lg text-[11px] font-mono capitalize transition-all ${
                        selectedTicket.status === st
                          ? 'bg-cyan-500 text-charcoal-950 font-bold shadow-glow-cyan'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      {st.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Recommended Next Action */}
              <div className="p-4 rounded-xl bg-cyan-500/10 border border-cyan-500/25">
                <span className="text-[10px] uppercase font-mono tracking-wider text-cyan-300 block mb-1 font-bold">
                  Recommended Action For Human Specialist:
                </span>
                <p className="text-xs text-white font-medium leading-relaxed">
                  {selectedTicket.recommended_action}
                </p>
              </div>

              {/* Specific Reason for Escalation */}
              <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/25">
                <span className="text-[10px] uppercase font-mono tracking-wider text-rose-300 block mb-1 font-bold">
                  Escalation Trigger:
                </span>
                <p className="text-xs text-slate-200 leading-relaxed font-mono">
                  {selectedTicket.reason}
                </p>
              </div>

              {/* Actions Attempted & Tools Used */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                  <span className="text-[10px] font-mono uppercase text-slate-400 block font-semibold">
                    Actions Attempted By AI:
                  </span>
                  <ul className="space-y-1 text-[11px] text-slate-300 list-disc list-inside">
                    {selectedTicket.actions_attempted?.map((a: string, idx: number) => (
                      <li key={idx} className="line-clamp-1">{a}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-3.5 rounded-xl bg-white/[0.02] border border-white/[0.06] space-y-2">
                  <span className="text-[10px] font-mono uppercase text-slate-400 block font-semibold">
                    Tools Executed:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedTicket.tools_used?.map((tool: string, idx: number) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-white/[0.05] text-[10px] font-mono text-cyan-300">
                        {tool}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-standard rounded-2xl p-12 text-center text-xs text-slate-400">
              Select an escalation ticket from the queue to view its AI handoff dossier.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
