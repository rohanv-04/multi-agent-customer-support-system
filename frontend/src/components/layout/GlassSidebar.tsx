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
  Activity
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export type NavTab =
  | 'overview'
  | 'cases'
  | 'customers'
  | 'agents'
  | 'automations'
  | 'knowledge'
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
  const navItems = [
    { id: 'overview' as NavTab, label: 'Overview', icon: LayoutDashboard },
    { id: 'cases' as NavTab, label: 'Cases', icon: Layers, badge: escalationCount },
    { id: 'customers' as NavTab, label: 'Customers', icon: Users },
    { id: 'agents' as NavTab, label: 'Agents', icon: Bot },
    { id: 'automations' as NavTab, label: 'Automations', icon: Zap },
    { id: 'knowledge' as NavTab, label: 'Knowledge', icon: BookOpen },
    { id: 'analytics' as NavTab, label: 'Analytics', icon: BarChart3 },
    { id: 'evaluations' as NavTab, label: 'Evaluations', icon: FlaskConical },
    { id: 'audit' as NavTab, label: 'Audit Logs', icon: Shield },
    { id: 'settings' as NavTab, label: 'Settings', icon: Settings },
    { id: 'chat' as NavTab, label: 'Customer Chat', icon: MessageSquareText, highlight: true },
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

        {/* Tenant & Role Footnote */}
        <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] text-[11px] text-slate-400">
          <div className="flex items-center justify-between text-slate-300 font-medium mb-1">
            <span className="font-mono text-cyan-400">{user?.organization_id || 'ORG-NOVACART'}</span>
            <span className="text-amber-400 text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-400/10 border border-amber-400/20">
              {user?.role || 'ADMIN'}
            </span>
          </div>
          <p className="text-[10px] text-slate-400 leading-relaxed truncate">
            {user?.email || 'admin@novacart.com'}
          </p>
        </div>
      </div>
    </aside>
  );
};
