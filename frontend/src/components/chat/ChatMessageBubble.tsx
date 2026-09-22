import React, { useState } from 'react';
import { Bot, User, ShieldCheck, AlertTriangle, ChevronDown, ChevronUp, Wrench, CheckCircle, Phone } from 'lucide-react';
import { ChatMessage } from '../../types';
import { HumanSupportCard } from './HumanSupportCard';

interface Props {
  message: ChatMessage;
  onOpenTicket?: (ticketId: string) => void;
}

export const ChatMessageBubble: React.FC<Props> = ({ message, onOpenTicket }) => {
  const [showTrace, setShowTrace] = useState(false);
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'} my-3`}>
      {/* Bot Avatar */}
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-cyan-500/30 to-blue-600/30 border border-cyan-400/30 flex items-center justify-center shrink-0 text-cyan-300">
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div className={`max-w-2xl flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Main Glass Bubble */}
        <div
          className={`p-4 rounded-2xl text-sm leading-relaxed ${
            isUser
              ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 border border-cyan-400/30 text-white rounded-br-none shadow-glow-cyan'
              : 'glass-standard text-slate-200 rounded-bl-none'
          }`}
        >
          {/* Header Metadata for Assistant */}
          {!isUser && (
            <div className="flex items-center gap-2 mb-2 border-b border-white/[0.08] pb-1.5 text-[11px] text-slate-400 font-mono">
              <span className="text-cyan-300 font-semibold">Supervisor Agent</span>
              {message.confidence && (
                <span className="px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  {Math.round(message.confidence * 100)}% Conf
                </span>
              )}
              {message.requires_escalation && (
                <span className="px-1.5 py-0.2 rounded bg-rose-500/15 text-rose-300 border border-rose-500/30 flex items-center gap-1">
                  <AlertTriangle className="w-2.5 h-2.5" />
                  Escalated
                </span>
              )}
            </div>
          )}

          {/* Formatted Message Content */}
          <div className="whitespace-pre-wrap font-sans text-sm">{message.content}</div>

          {/* Escalation Ticket Box if applicable */}
          {message.escalation_dossier && (
            <div className="mt-3 p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs">
              <div className="flex items-center justify-between font-mono font-semibold text-rose-300 mb-1">
                <span>SUPPORT TICKET #{message.escalation_dossier.ticket_id}</span>
                <span className="text-[10px] bg-rose-500/20 px-2 py-0.5 rounded">HIGH PRIORITY</span>
              </div>
              <p className="text-slate-300 text-[11px] leading-snug">
                {message.escalation_dossier.summary}
              </p>
              <div className="mt-2 text-[10px] text-slate-400 font-mono">
                Reason: {message.escalation_dossier.reason}
              </div>
            </div>
          )}

          {/* Inline Human Support Action Card for Escalated Messages */}
          {!isUser && (message.requires_escalation || message.content.toLowerCase().includes('human support') || message.escalation_dossier) && (
            <div className="mt-3">
              <HumanSupportCard
                caseId={message.case_id || null}
                customerId="CUST1002"
              />
            </div>
          )}

          {/* Tool Calls Summary Pill */}
          {message.tool_calls && message.tool_calls.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {message.tool_calls.map((tc, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.1] text-[10px] text-slate-300 font-mono flex items-center gap-1"
                >
                  <Wrench className="w-2.5 h-2.5 text-cyan-400" />
                  {tc.tool_name}
                </span>
              ))}
            </div>
          )}

          {/* Trace Accordion Toggle */}
          {message.execution_trace && message.execution_trace.length > 0 && (
            <div className="mt-3 pt-2 border-t border-white/[0.06]">
              <button
                onClick={() => setShowTrace(!showTrace)}
                className="flex items-center gap-1 text-[10px] text-cyan-400 font-mono hover:text-cyan-300 transition-colors"
              >
                <span>{showTrace ? 'Hide' : 'View'} Execution Trace ({message.execution_trace.length} steps)</span>
                {showTrace ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              </button>

              {showTrace && (
                <div className="mt-2 space-y-1 max-h-40 overflow-y-auto pr-1">
                  {message.execution_trace.map((tr, i) => (
                    <div key={i} className="text-[10px] font-mono text-slate-400 flex items-start gap-1.5 bg-black/30 p-1.5 rounded">
                      <span className="text-cyan-400">{tr.timestamp}</span>
                      <strong className="text-slate-200">[{tr.agent}]:</strong>
                      <span className="text-slate-300">{tr.action}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Timestamp */}
        <span className="text-[10px] text-slate-400 mt-1 px-1 font-mono">
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
