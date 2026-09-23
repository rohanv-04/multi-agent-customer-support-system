import React, { useState, useEffect } from 'react';
import { ThemeProvider } from './context/ThemeContext';
import { AmbientBackground } from './components/layout/AmbientBackground';
import { GlassNavbar } from './components/layout/GlassNavbar';
import { GlassSidebar, NavTab } from './components/layout/GlassSidebar';
import { CommandCenterView } from './pages/CommandCenterView';
import { CasesManagementView } from './pages/CasesManagementView';
import { CaseDetailView } from './pages/CaseDetailView';
import { CustomersView } from './pages/CustomersView';
import { AgentOperationsView } from './pages/AgentOperationsView';
import { AutomationsView } from './pages/AutomationsView';
import { CustomerChatView } from './pages/CustomerChatView';
import { AgentWorkflowView } from './pages/AgentWorkflowView';
import { KnowledgeView } from './pages/KnowledgeView';
import { AnalyticsView } from './pages/AnalyticsView';
import { EvaluationLabView } from './pages/EvaluationLabView';
import { AuditLogExplorerView } from './pages/AuditLogExplorerView';
import { UserManagementView } from './pages/UserManagementView';
import { RootCausesView } from './pages/RootCausesView';
import { SimulationLabView } from './pages/SimulationLabView';
import { AuthProvider } from './context/AuthContext';
import { AgentModal } from './components/agents/AgentModal';
import { Customer, AgentInfo, AnalyticsData, AIState } from './types';
import { getCustomers, getAgents, getAnalytics, getEscalations } from './services/api';

export function AppContent() {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [casesFilter, setCasesFilter] = useState<string | undefined>(undefined);
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
    <div className="relative min-h-screen flex flex-col text-slate-900 dark:text-slate-100 overflow-x-hidden transition-colors duration-300">
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
          {activeTab === 'overview' && (
            <CommandCenterView
              onNavigateToCases={(filter) => {
                setCasesFilter(filter);
                setSelectedCaseId(null);
                setActiveTab('cases');
              }}
              onNavigateToCaseDetail={(cId) => {
                setSelectedCaseId(cId);
                setActiveTab('cases');
              }}
              onNavigateToAgents={() => setActiveTab('agents')}
            />
          )}

          {activeTab === 'cases' && (
            selectedCaseId ? (
              <CaseDetailView
                caseId={selectedCaseId}
                onBack={() => setSelectedCaseId(null)}
              />
            ) : (
              <CasesManagementView
                onSelectCase={(cId) => setSelectedCaseId(cId)}
                initialFilter={casesFilter}
              />
            )
          )}

          {activeTab === 'customers' && (
            <CustomersView
              onSelectCustomerToChat={(cust) => {
                setCurrentCustomer(cust);
                setActiveTab('chat');
              }}
              onCreateCaseForCustomer={(cId) => {
                setActiveTab('cases');
              }}
            />
          )}

          {activeTab === 'agents' && <AgentOperationsView />}

          {activeTab === 'automations' && <AutomationsView />}

          {activeTab === 'knowledge' && <KnowledgeView />}

          {activeTab === 'root_causes' && <RootCausesView />}

          {activeTab === 'simulation' && <SimulationLabView />}

          {activeTab === 'analytics' && <AnalyticsView analytics={analytics} />}

          {activeTab === 'evaluations' && <EvaluationLabView />}

          {activeTab === 'audit' && <AuditLogExplorerView />}

          {activeTab === 'settings' && <UserManagementView />}

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

          {activeTab === 'workflow' && (
            <AgentWorkflowView
              agents={agents}
              onSelectAgent={handleSelectAgentById}
            />
          )}
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

export function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
