import React, { useState } from 'react';
import { 
  Zap, 
  ShieldCheck, 
  Clock, 
  AlertTriangle, 
  CheckCircle2, 
  Sliders, 
  Activity, 
  Radio, 
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AutomationsView: React.FC = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'proactive' | 'gateway' | 'sla'>('proactive');

  const PROACTIVE_RULES = [
    {
      id: 'EVT-001',
      event: 'Carrier Shipment Delay',
      trigger: 'Carrier tracking shows >24h delay past expected delivery window',
      action: 'Auto-create SupportCase, evaluate Delay Compensation Policy, notify customer via active channel',
      status: 'Active',
      casesTriggered: 18
    },
    {
      id: 'EVT-002',
      event: 'Payment Settlement Failure',
      trigger: 'Payment processor reports charge attempt decline or dispute',
      action: 'Triage billing failure, check payment retry rules, dispatch secure update link',
      status: 'Active',
      casesTriggered: 7
    },
    {
      id: 'EVT-003',
      event: 'Repeated Failed Delivery',
      trigger: 'Carrier reports 2 consecutive failed delivery attempts',
      action: 'Escalate to human dispatcher, verify customer phone & delivery address',
      status: 'Active',
      casesTriggered: 4
    },
    {
      id: 'EVT-004',
      event: 'SLA Breach Proactive Watcher',
      trigger: 'Case remaining SLA time drops below 30 minutes without active agent action',
      action: 'Bump priority to urgent, re-assign supervisor, ping active queue',
      status: 'Active',
      casesTriggered: 12
    }
  ];

  const GATEWAY_RULES = [
    {
      action: 'Refund Request (< $50)',
      riskLevel: 'LOW RISK',
      gate: 'Autonomous Execution',
      verification: 'Post-action DB balance & transaction check'
    },
    {
      action: 'Refund Request (≥ $50)',
      riskLevel: 'MEDIUM / HIGH RISK',
      gate: 'Supervisor Manual Approval Required',
      verification: 'Supervisor review + state audit log'
    },
    {
      action: 'Order Cancellation (Pre-fulfillment)',
      riskLevel: 'LOW RISK',
      gate: 'Autonomous Execution',
      verification: 'Warehouse cancellation lock & refund trigger'
    },
    {
      action: 'Replacement & Reshipment',
      riskLevel: 'MEDIUM RISK',
      gate: 'Autonomous Execution if VIP, else Approval',
      verification: 'Carrier tracking issuance & inventory decrement'
    }
  ];

  const SLA_POLICIES = [
    { priority: 'Urgent', responseTime: '15 minutes', resolutionTarget: '2 hours', escalationThreshold: '30 minutes' },
    { priority: 'High', responseTime: '30 minutes', resolutionTarget: '4 hours', escalationThreshold: '60 minutes' },
    { priority: 'Medium', responseTime: '1 hour', resolutionTarget: '8 hours', escalationThreshold: '2 hours' },
    { priority: 'Low', responseTime: '2 hours', resolutionTarget: '24 hours', escalationThreshold: '6 hours' },
  ];

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-[1700px] mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-gradient-to-tr from-cyan-600 to-blue-600 rounded-xl shadow-lg shadow-cyan-500/20 text-white">
              <Zap className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">Support Automations & Proactive Engine</h1>
              <p className="text-xs text-slate-400 font-mono">
                Event Monitors, Action Gateway Thresholds, and SLA Policies • Tenant: <span className="text-cyan-400 font-semibold">{user?.organization_id}</span>
              </p>
            </div>
          </div>
        </div>

        {/* Tab Pills */}
        <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-xl">
          <button
            onClick={() => setActiveTab('proactive')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'proactive' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white'
            }`}
          >
            Proactive Monitors
          </button>
          <button
            onClick={() => setActiveTab('gateway')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'gateway' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white'
            }`}
          >
            Action Gateway
          </button>
          <button
            onClick={() => setActiveTab('sla')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'sla' ? 'bg-cyan-500 text-slate-950 shadow-md' : 'text-slate-400 hover:text-white'
            }`}
          >
            SLA Policies
          </button>
        </div>
      </div>

      {/* TAB 1: PROACTIVE BUSINESS EVENT MONITORS */}
      {activeTab === 'proactive' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {PROACTIVE_RULES.map((rule) => (
            <div key={rule.id} className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-bold text-cyan-400">{rule.id}</span>
                <span className="flex items-center gap-1.5 text-xs text-emerald-400 font-medium font-mono">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  {rule.status}
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-white">{rule.event}</h3>
                <div className="mt-2 text-xs text-slate-300">
                  <strong className="text-slate-400 font-mono">Trigger Condition:</strong> {rule.trigger}
                </div>
                <div className="mt-1 text-xs text-slate-300">
                  <strong className="text-purple-400 font-mono">Autonomous Action:</strong> {rule.action}
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                <span>Cases Triggered This Month:</span>
                <span className="font-bold font-mono text-white">{rule.casesTriggered}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* TAB 2: ACTION GATEWAY RULES */}
      {activeTab === 'gateway' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-purple-400" />
                Action Gateway Risk & Approval Matrix
              </h2>
              <p className="text-xs text-slate-400">
                No AI specialist agent executes sensitive financial or stateful mutations without gateway validation.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 font-semibold">
                  <th className="py-3 px-4">Action Type</th>
                  <th className="py-3 px-4">Risk Classification</th>
                  <th className="py-3 px-4">Execution Guardrail</th>
                  <th className="py-3 px-4">Verification Layer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {GATEWAY_RULES.map((g, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30">
                    <td className="py-3.5 px-4 font-bold text-slate-200">
                      {g.action}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        g.riskLevel.includes('HIGH') ? 'bg-amber-500/20 text-amber-300' : 'bg-emerald-500/20 text-emerald-300'
                      }`}>
                        {g.riskLevel}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">
                      {g.gate}
                    </td>
                    <td className="py-3.5 px-4 text-slate-400 font-mono">
                      {g.verification}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 3: SLA POLICIES */}
      {activeTab === 'sla' && (
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-md space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Clock className="w-5 h-5 text-amber-400" />
                Service Level Agreement (SLA) Targets
              </h2>
              <p className="text-xs text-slate-400">
                Dynamic deadlines calculated based on customer tier, priority, and channel.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {SLA_POLICIES.map((p) => (
              <div key={p.priority} className="p-4 rounded-xl bg-slate-800/40 border border-slate-700 space-y-3">
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-bold uppercase ${
                    p.priority === 'Urgent' ? 'text-red-400' :
                    p.priority === 'High' ? 'text-amber-400' :
                    p.priority === 'Medium' ? 'text-blue-400' :
                    'text-slate-400'
                  }`}>
                    {p.priority} Priority
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-slate-300">
                  <div>First Response: <strong className="text-cyan-300 font-mono">{p.responseTime}</strong></div>
                  <div>Resolution Target: <strong className="text-emerald-300 font-mono">{p.resolutionTarget}</strong></div>
                  <div>Escalation Warning: <strong className="text-amber-300 font-mono">{p.escalationThreshold}</strong></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
