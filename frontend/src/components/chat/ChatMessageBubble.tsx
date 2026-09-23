import React, { useState } from 'react';
import { Sparkles, User, AlertTriangle, ChevronDown, ChevronUp, Wrench, ShieldCheck } from 'lucide-react';
import { ChatMessage } from '../../types';

interface Props {
  message: ChatMessage;
  onOpenTicket?: (ticketId: string) => void;
}

export const ChatMessageBubble: React.FC<Props> = ({ message }) => {
  const [showTrace, setShowTrace] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'} my-3`}>
      {/* Bot Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-blue-600/30 border border-cyan-400/30 flex items-center justify-center shrink-0 text-cyan-300 shadow-sm">
          <Sparkles className="w-4 h-4 text-cyan-400" />
        </div>
      )}

      <div className={`max-w-2xl flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Main Glass Bubble */}
        <div
          className={`p-4 rounded-2xl text-sm leading-relaxed transition-all ${
            isUser
              ? 'bg-gradient-to-r from-cyan-600 to-blue-600 text-white rounded-br-none shadow-md shadow-cyan-900/20'
              : 'glass-standard text-slate-800 dark:text-slate-100 rounded-bl-none'
          }`}
        >
          {/* Header for Assistant */}
          {!isUser && (
            <div className="flex items-center justify-between gap-3 mb-2 border-b border-slate-200 dark:border-white/[0.08] pb-1 text-[11px] text-slate-500 dark:text-slate-400 font-sans">
              <span className="text-cyan-700 dark:text-cyan-300 font-semibold tracking-wide">SupportOS AI</span>
              {message.requires_escalation && (
                <span className="px-2 py-0.5 rounded-full bg-rose-500/15 text-rose-700 dark:text-rose-300 border border-rose-500/30 text-[10px] font-medium flex items-center gap-1">
                  <AlertTriangle className="w-2.5 h-2.5" />
                  Support Desk
                </span>
              )}
            </div>
          )}

          {/* Formatted Message Content */}
          <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-slate-800 dark:text-slate-100">
            {message.content}
          </div>

          {/* Escalation Ticket Pill if case is escalated */}
          {message.escalation_dossier && (
            <div className="mt-3 p-2.5 rounded-xl bg-slate-100/90 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                  Ticket #{message.escalation_dossier.ticket_id}
                </span>
              </div>
              <span className="text-[10px] text-cyan-700 dark:text-cyan-300 font-mono">
                Assigned to Support Desk
              </span>
            </div>
          )}

          {/* Developer Diagnostics Accordion (collapsible) */}
          {message.execution_trace && message.execution_trace.length > 0 && (
            <div className="mt-3 pt-2 border-t border-slate-200 dark:border-white/[0.06]">
              <button
                onClick={() => setShowTrace(!showTrace)}
                className="flex items-center gap-1 text-[10px] text-slate-500 dark:text-slate-400 hover:text-cyan-600 dark:hover:text-cyan-300 font-mono transition-colors"
              >
                <span>{showTrace ? 'Hide' : 'Inspect'} AI Actions ({message.execution_trace.length} diagnostics)</span>
                {showTrace ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>

              {showTrace && (
                <div className="mt-2 space-y-1 max-h-36 overflow-y-auto pr-1">
                  {message.execution_trace.map((tr, i) => (
                    <div key={i} className="text-[10px] font-mono text-slate-600 dark:text-slate-400 flex items-start gap-1.5 bg-slate-100/80 dark:bg-black/40 p-1.5 rounded border border-slate-200/60 dark:border-transparent">
                      <span className="text-cyan-700 dark:text-cyan-400">{tr.timestamp}</span>
                      <strong className="text-slate-700 dark:text-slate-300">[{tr.agent}]:</strong>
                      <span className="text-slate-600 dark:text-slate-400">{tr.action}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-1 px-1 font-mono">
          {message.timestamp}
        </span>
      </div>

      {/* User Avatar */}
      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-white/[0.08] border border-white/[0.15] flex items-center justify-center shrink-0 text-slate-300">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
};
