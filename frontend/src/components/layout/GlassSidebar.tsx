import React from 'react';
import {
  LayoutDashboard,
  MessageSquareText,
  Network,
  ListTodo,
  Brain,
  BookOpen,
  UserCheck,
  BarChart3,
  Settings
} from 'lucide-react';

export type NavTab =
  | 'dashboard'
  | 'chat'
  | 'workflow'
  | 'tasks'
  | 'memory'
  | 'knowledge'
  | 'escalations'
  | 'analytics'
  | 'settings';

interface Props {
  activeTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
  escalationCount?: number;
}

export const GlassSidebar: React.FC<Props> = ({ activeTab, onSelectTab, escalationCount = 0 }) => {
  const navItems = [
    { id: 'dashboard' as NavTab, label: 'Dashboard', icon: LayoutDashboard },
    { id: 'chat' as NavTab, label: 'Customer Chat', icon: MessageSquareText, highlight: true },
    { id: 'workflow' as NavTab, label: 'Agent Workflow', icon: Network },
    { id: 'tasks' as NavTab, label: 'Tasks', icon: ListTodo },
    { id: 'memory' as NavTab, label: 'Memory', icon: Brain },
    { id: 'knowledge' as NavTab, label: 'Knowledge Base', icon: BookOpen },
    { id: 'escalations' as NavTab, label: 'Escalations', icon: UserCheck, badge: escalationCount },
    { id: 'analytics' as NavTab, label: 'Analytics', icon: BarChart3 },
    { id: 'settings' as NavTab, label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 shrink-0 hidden lg:block">
      <div className="glass-standard rounded-2xl p-3 h-[calc(100vh-6.5rem)] sticky top-20 flex flex-col justify-between">
        <div className="space-y-1.5">
          <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 font-mono">
            Navigation
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-glow-cyan'
                    : 'text-slate-300 hover:text-white hover:bg-white/[0.04] border border-transparent'
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${
                      isActive ? 'text-cyan-300' : 'text-slate-400 group-hover:text-slate-200'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>

                {item.badge !== undefined && item.badge > 0 && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500/20 text-rose-300 border border-rose-500/30 animate-pulse">
                    {item.badge}
                  </span>
                )}

                {item.highlight && !isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                )}
              </button>
            );
          })}
        </div>

        {/* System Footnote */}
        <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] text-[11px] text-slate-400">
          <div className="flex items-center justify-between text-slate-300 font-medium mb-1">
            <span>LangGraph Engine</span>
            <span className="text-emerald-400 text-[10px]">v1.0 Ready</span>
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed">
            Real dynamic routing, replanning loop, & controlled database tools.
          </p>
        </div>
      </div>
    </aside>
  );
};
