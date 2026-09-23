import React from 'react';
import {
  LayoutDashboard,
  Layers,
  Users,
  Bot,
  Zap,
  BookOpen,
  BarChart3,
  FlaskConical,
  Shield,
  Settings,
  MessageSquareText,
  Activity,
  ChevronRight
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export type NavTab =
  | 'overview'
  | 'cases'
  | 'customers'
  | 'agents'
  | 'automations'
  | 'knowledge'
  | 'root_causes'
  | 'simulation'
  | 'analytics'
  | 'evaluations'
  | 'audit'
  | 'settings'
  | 'chat'
  | 'workflow';

interface Props {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  escalationCount?: number;
}

export const GlassSidebar: React.FC<Props> = ({ activeTab, onSelectTab, escalationCount = 0 }) => {
  const { user } = useAuth();

  const standardNavItems = [
    { id: 'overview' as NavTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'cases' as NavTab, label: 'Cases', icon: Layers, badge: escalationCount },
    { id: 'customers' as NavTab, label: 'Customers', icon: Users },
    { id: 'root_causes' as NavTab, label: 'Root Causes', icon: Activity },
    { id: 'simulation' as NavTab, label: 'Simulation Lab', icon: FlaskConical },
    { id: 'agents' as NavTab, label: 'Agents', icon: Bot },
    { id: 'automations' as NavTab, label: 'Automations', icon: Zap },
    { id: 'knowledge' as NavTab, label: 'Knowledge', icon: BookOpen },
    { id: 'analytics' as NavTab, label: 'Analytics', icon: BarChart3 },
    { id: 'evaluations' as NavTab, label: 'Evaluations', icon: Shield },
    { id: 'audit' as NavTab, label: 'Audit Logs', icon: Shield },
    { id: 'settings' as NavTab, label: 'Settings', icon: Settings },
  ];

  const isChatActive = activeTab === 'chat';

  return (
    <aside className="w-64 shrink-0 hidden lg:block select-none">
      <div className="glass-standard rounded-2xl p-3 h-[calc(100vh-6.5rem)] sticky top-20 flex flex-col justify-between overflow-hidden box-border">
        {/* TOP SECTION: Header & Scrollable Navigation */}
        <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
          <div className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 font-mono shrink-0">
            Navigation
          </div>

          {/* Scrollable Nav Item List */}
          <div className="flex-1 overflow-y-auto pr-1 space-y-1 my-1">
            {standardNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium transition-all duration-150 group ${
                    isActive
                      ? 'bg-cyan-500/15 text-cyan-800 dark:text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10 font-semibold'
                      : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-white/[0.04] border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Icon
                      className={`w-4 h-4 shrink-0 transition-transform duration-150 group-hover:scale-110 ${
                        isActive
                          ? 'text-cyan-600 dark:text-cyan-300'
                          : 'text-slate-500 dark:text-slate-400 group-hover:text-slate-700 dark:group-hover:text-slate-200'
                      }`}
                    />
                    <span className="truncate">{item.label}</span>
                  </div>

                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-600 dark:text-rose-300 border border-rose-500/30 animate-pulse shrink-0">
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* MIDDLE SECTION: Dedicated Customer Chat Item (Fully Contained) */}
        <div className="pt-2 pb-2 border-t border-slate-200/80 dark:border-white/[0.08] shrink-0">
          <button
            onClick={() => onSelectTab('chat')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all duration-150 group ${
              isChatActive
                ? 'bg-gradient-to-r from-cyan-500/20 to-blue-600/20 text-cyan-800 dark:text-cyan-200 border border-cyan-400/40 shadow-sm'
                : 'bg-slate-100/80 dark:bg-white/[0.03] text-slate-700 dark:text-slate-200 hover:bg-slate-200/70 dark:hover:bg-white/[0.07] border border-slate-200 dark:border-white/[0.08] hover:border-cyan-400/30'
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-6 h-6 rounded-lg bg-cyan-500/20 flex items-center justify-center shrink-0 text-cyan-600 dark:text-cyan-300">
                <MessageSquareText className="w-3.5 h-3.5" />
              </div>
              <div className="text-left min-w-0">
                <div className="truncate font-bold">Customer Chat</div>
                <div className="text-[10px] text-slate-500 dark:text-slate-400 font-normal">Live AI Support</div>
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {!isChatActive && <span className="w-2 h-2 rounded-full bg-cyan-500 animate-pulse" />}
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
            </div>
          </button>
        </div>

        {/* BOTTOM SECTION: Tenant & Admin Footnote */}
        <div className="p-2.5 rounded-xl bg-slate-100/80 dark:bg-white/[0.02] border border-slate-200/90 dark:border-white/[0.05] text-[11px] shrink-0">
          <div className="flex items-center justify-between text-slate-700 dark:text-slate-300 font-medium mb-1">
            <span className="font-mono text-cyan-700 dark:text-cyan-400 font-semibold text-xs">
              {user?.organization_id || 'ORG-NOVACART'}
            </span>
            <span className="text-amber-700 dark:text-amber-400 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20">
              {user?.role || 'ADMIN'}
            </span>
          </div>
          <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-relaxed truncate font-mono">
            {user?.email || 'admin@novacart.com'}
          </p>
        </div>
      </div>
    </aside>
  );
};
