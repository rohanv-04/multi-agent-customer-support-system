import React from 'react';
import { Play, Sparkles, RefreshCw, UserCheck, Search, Wrench } from 'lucide-react';

interface Props {
  onRunScenario: (prompt: string, customerId?: string) => void;
  disabled?: boolean;
}

export const DemoScenarioLauncher: React.FC<Props> = ({ onRunScenario, disabled }) => {
  const scenarios = [
    {
      id: 's3',
      title: 'Scenario 3: Autonomous Refund (Primary Demo)',
      prompt: "My order ORD10002 is delayed. If I'm eligible, refund it.",
      customerId: 'CUST1002',
      badge: 'Autonomous Action',
      badgeColor: 'bg-cyan-500/20 text-cyan-300 border-cyan-400/30',
      icon: Sparkles
    },
    {
      id: 's1',
      title: 'Scenario 1: Policy Knowledge Retrieval (RAG)',
      prompt: 'What is your refund policy?',
      customerId: 'CUST1001',
      badge: 'RAG Retrieval',
      badgeColor: 'bg-blue-500/20 text-blue-300 border-blue-400/30',
      icon: Search
    },
    {
      id: 's2',
      title: 'Scenario 2: Multi-Step Reasoning & Eligibility',
      prompt: "Check order ORD10001 and tell me if I'm eligible for a refund.",
      customerId: 'CUST1001',
      badge: 'Multi-Step',
      badgeColor: 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30',
      icon: Wrench
    },
    {
      id: 's4',
      title: 'Scenario 4: Re-Planning on Tool Failure',
      prompt: 'Check order ORD99999 and refund it.',
      customerId: 'CUST1001',
      badge: 'Re-Planning Loop',
      badgeColor: 'bg-amber-500/20 text-amber-300 border-amber-400/30',
      icon: RefreshCw
    },
    {
      id: 's5',
      title: 'Scenario 5: Human Support Escalation',
      prompt: 'I want to speak to a human.',
      customerId: 'CUST1001',
      badge: 'Human Handoff',
      badgeColor: 'bg-rose-500/20 text-rose-300 border-rose-400/30',
      icon: UserCheck
    },
  ];

  return (
    <div className="glass-subtle rounded-2xl p-3 mb-3 border border-white/[0.08]">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5 text-[11px] font-mono uppercase text-slate-400">
          <Play className="w-3 h-3 text-cyan-400" />
          <span>Quick Demo Scenarios</span>
        </div>
        <span className="text-[10px] text-slate-400">Click to execute live</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2">
        {scenarios.map((sc) => {
          const Icon = sc.icon;
          return (
            <button
              key={sc.id}
              disabled={disabled}
              onClick={() => onRunScenario(sc.prompt, sc.customerId)}
              className="p-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.08] hover:border-cyan-400/40 text-left transition-all duration-200 group disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <div className="flex items-center justify-between gap-1 mb-1">
                <span className={`px-2 py-0.5 rounded-full text-[9px] font-semibold border ${sc.badgeColor}`}>
                  {sc.badge}
                </span>
                <Icon className="w-3 h-3 text-slate-400 group-hover:text-cyan-300 transition-colors" />
              </div>
              <p className="text-[11px] font-medium text-slate-200 group-hover:text-white line-clamp-1">
                {sc.title}
              </p>
              <p className="text-[10px] text-slate-400 italic line-clamp-1 mt-0.5">
                "{sc.prompt}"
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};
