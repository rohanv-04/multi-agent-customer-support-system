import React, { useState, useEffect } from 'react';
import { AmbientBackground } from './components/layout/AmbientBackground';
import { GlassNavbar } from './components/layout/GlassNavbar';
import { GlassSidebar, NavTab } from './components/layout/GlassSidebar';
import { CustomerChatView } from './pages/CustomerChatView';
import { DashboardView } from './pages/DashboardView';
import { AgentWorkflowView } from './pages/AgentWorkflowView';
import { TasksView } from './pages/TasksView';
import { MemoryView } from './pages/MemoryView';
import { KnowledgeView } from './pages/KnowledgeView';
import { EscalationsView } from './pages/EscalationsView';
import { AnalyticsView } from './pages/AnalyticsView';
import { SettingsView } from './pages/SettingsView';
import { AgentModal } from './components/agents/AgentModal';
import { Customer, AgentInfo, AnalyticsData, AIState } from './types';
import { getCustomers, getAgents, getAnalytics, getEscalations } from './services/api';

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('chat');
  const [aiState, setAiState] = useState<AIState>('IDLE');
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [currentCustomer, setCurrentCustomer] = useState<Customer | null>(null);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [escalationCount, setEscalationCount] = useState<number>(0);

  // Initial load
  useEffect(() => {
    const initData = async () => {
      try {
        const [custRes, agentRes, analyticsRes, escRes] = await Promise.all([
          getCustomers(),
          getAgents(),
          getAnalytics(),
          getEscalations('open')
        ]);

        if (custRes.customers && custRes.customers.length > 0) {
          setCustomers(custRes.customers);
          // Default to CUST1002 (Elena Rostova) for primary demo
          const elena = custRes.customers.find((c: Customer) => c.customer_id === 'CUST1002') || custRes.customers[0];
          setCurrentCustomer(elena);
        }

        if (agentRes.agents) {
          setAgents(agentRes.agents);
        }

        if (analyticsRes) {
          setAnalytics(analyticsRes);
        }

        if (escRes.tickets) {
          setEscalationCount(escRes.tickets.length);
        }
      } catch (err) {
        console.error('Failed to load initial system data:', err);
      }
    };

    initData();
  }, []);

  const refreshEscalationCount = async () => {
    try {
      const escRes = await getEscalations('open');
      if (escRes.tickets) setEscalationCount(escRes.tickets.length);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSelectAgentById = (agentId: string) => {
    const found = agents.find((a) => a.id === agentId || a.name.toLowerCase().includes(agentId.toLowerCase()));
    if (found) setSelectedAgent(found);
  };

  return (
    <div className="relative min-h-screen flex flex-col text-slate-100 overflow-x-hidden">
      {/* Dynamic Ambient Background reacting to AI lifecycle */}
      <AmbientBackground aiState={aiState} />

      {/* Floating Glass Top Bar */}
      <GlassNavbar
        currentCustomer={currentCustomer}
        customers={customers}
        onSelectCustomer={(c) => setCurrentCustomer(c)}
        systemStatus={analytics?.system_status || 'All systems operational'}
      />

      {/* Floating Main Layout */}
      <div className="flex-1 flex gap-5 px-4 sm:px-6 py-4 max-w-[1700px] w-full mx-auto relative z-10">
        {/* Floating Translucent Sidebar */}
        <GlassSidebar
          activeTab={activeTab}
          onSelectTab={(tab) => setActiveTab(tab)}
          escalationCount={escalationCount}
        />

        {/* Main Floating Workspace */}
        <main className="flex-1 min-w-0">
          {activeTab === 'chat' && (
            <CustomerChatView
              currentCustomer={currentCustomer}
              agents={agents}
              onSelectAgent={handleSelectAgentById}
              aiState={aiState}
              setAiState={setAiState}
              onTicketCreated={refreshEscalationCount}
            />
          )}

          {activeTab === 'dashboard' && (
            <DashboardView
              analytics={analytics}
              onNavigateToChat={() => setActiveTab('chat')}
              onNavigateToEscalations={() => setActiveTab('escalations')}
            />
          )}

          {activeTab === 'workflow' && (
            <AgentWorkflowView
              agents={agents}
              onSelectAgent={handleSelectAgentById}
            />
          )}

          {activeTab === 'tasks' && <TasksView />}

          {activeTab === 'memory' && <MemoryView currentCustomer={currentCustomer} />}

          {activeTab === 'knowledge' && <KnowledgeView />}

          {activeTab === 'escalations' && <EscalationsView />}

          {activeTab === 'analytics' && <AnalyticsView analytics={analytics} />}

          {activeTab === 'settings' && <SettingsView />}
        </main>
      </div>

      {/* Agent Detail Floating Modal */}
      <AgentModal
        agent={selectedAgent}
        onClose={() => setSelectedAgent(null)}
      />
    </div>
  );
}

export default App;
