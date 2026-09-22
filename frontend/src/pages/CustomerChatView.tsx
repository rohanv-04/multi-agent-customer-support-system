import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Loader2, RefreshCw } from 'lucide-react';
import { ChatMessage, Customer, TraceEvent, AIState, AgentInfo, InvestigationResult } from '../types';
import { ChatMessageBubble } from '../components/chat/ChatMessageBubble';
import { AIExecutionPanel } from '../components/chat/AIExecutionPanel';
import { SpatialAgentGraph } from '../components/chat/SpatialAgentGraph';
import { CustomerContextCard } from '../components/chat/CustomerContextCard';
import { DemoScenarioLauncher } from '../components/chat/DemoScenarioLauncher';
import { sendMessage, streamChatMessage } from '../services/api';

interface Props {
  currentCustomer: Customer | null;
  agents: AgentInfo[];
  onSelectAgent: (agentId: string) => void;
  aiState: AIState;
  setAiState: (state: AIState) => void;
  onTicketCreated?: () => void;
}

export const CustomerChatView: React.FC<Props> = ({
  currentCustomer,
  agents,
  onSelectAgent,
  aiState,
  setAiState,
  onTicketCreated
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-1',
      role: 'assistant',
      content:
        "Hello! I am AgentSupport AI, your autonomous customer support specialist for NovaCart.\n\nI can track packages, verify refund eligibility, retrieve company policies, investigate multi-source records, and process actions directly. How can I help you today?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      confidence: 1.0,
      status: 'completed'
    }
  ]);

  const [inputText, setInputText] = useState('');
  const [activeGoal, setActiveGoal] = useState<string>('');
  const [activePlan, setActivePlan] = useState<string[]>([]);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [currentStep, setCurrentStep] = useState<string>('');
  const [confidence, setConfidence] = useState<number>(0.94);
  const [replanCount, setReplanCount] = useState<number>(0);
  const [activeAgentName, setActiveAgentName] = useState<string>('Supervisor Agent');
  const [liveTraceEvents, setLiveTraceEvents] = useState<TraceEvent[]>([]);
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [investigationResult, setInvestigationResult] = useState<InvestigationResult | null>(null);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, liveTraceEvents]);

  const handleSend = async (customText?: string, targetCustomerId?: string) => {
    const textToSend = customText || inputText;
    if (!textToSend.trim() || aiState === 'EXECUTING') return;

    const custId = targetCustomerId || currentCustomer?.customer_id || 'CUST1002';

    // Add user message
    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');

    // Update AI state
    setAiState('THINKING');
    setActiveGoal(textToSend);
    setActivePlan([]);
    setCompletedSteps([]);
    setLiveTraceEvents([]);
    setReplanCount(0);
    setActiveAgentName('Supervisor Agent');
    setInvestigationResult(null);

    try {
      // Use streaming endpoint
      streamChatMessage(
        textToSend,
        custId,
        undefined,
        activeCaseId || undefined,
        (trace: TraceEvent) => {
          setLiveTraceEvents((prev) => [...prev, trace]);
          setActiveAgentName(trace.agent);

          if (trace.agent.toLowerCase().includes('plan')) {
            setAiState('PLANNING');
            if (trace.details?.steps) {
              setActivePlan(trace.details.steps);
            }
          } else if (trace.agent.toLowerCase().includes('tool') || trace.agent.toLowerCase().includes('resolution')) {
            setAiState('EXECUTING');
            setCurrentStep(trace.action);
            setCompletedSteps((prev) => [...new Set([...prev, trace.action])]);
          } else if (trace.agent.toLowerCase().includes('critic')) {
            setAiState('VALIDATING');
          } else if (trace.action.toLowerCase().includes('re-planning')) {
            setAiState('REPLANNING');
            setReplanCount((prev) => prev + 1);
          } else if (trace.agent.toLowerCase().includes('escalation')) {
            setAiState('ESCALATED');
            if (onTicketCreated) onTicketCreated();
          }
        },
        (completion: any) => {
          setActivePlan(completion.plan || []);
          setCompletedSteps(completion.completed_steps || completion.plan || []);
          setConfidence(completion.confidence || 0.95);
          setAiState(completion.requires_escalation ? 'ESCALATED' : 'COMPLETED');
          if (completion.case_id) setActiveCaseId(completion.case_id);
          if (completion.investigation_result) setInvestigationResult(completion.investigation_result);

          // Add assistant message
          const assistantMsg: ChatMessage = {
            id: `msg-${Date.now()}-ai`,
            role: 'assistant',
            content: completion.response,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            task_id: completion.task_id,
            case_id: completion.case_id,
            confidence: completion.confidence,
            status: completion.status,
            execution_trace: liveTraceEvents,
            plan: completion.plan,
            completed_steps: completion.completed_steps,
            investigation_result: completion.investigation_result,
            customer_360: completion.customer_360,
            requires_escalation: completion.requires_escalation,
            escalation_dossier: completion.escalation_dossier
          };

          setMessages((prev) => [...prev, assistantMsg]);
        },
        async () => {
          // If streaming connection fails, fallback seamlessly to JSON endpoint
          const res = await sendMessage(textToSend, custId, undefined, activeCaseId || undefined);
          setActivePlan(res.plan || []);
          setCompletedSteps(res.completed_steps || []);
          setConfidence(res.confidence || 0.95);
          setLiveTraceEvents(res.execution_trace || []);
          setAiState(res.requires_escalation ? 'ESCALATED' : 'COMPLETED');
          if (res.case_id) setActiveCaseId(res.case_id);
          if (res.investigation_result) setInvestigationResult(res.investigation_result);

          const assistantMsg: ChatMessage = {
            id: `msg-${Date.now()}-ai`,
            role: 'assistant',
            content: res.response,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            task_id: res.task_id,
            case_id: res.case_id,
            confidence: res.confidence,
            status: res.status,
            execution_trace: res.execution_trace,
            plan: res.plan,
            completed_steps: res.completed_steps,
            investigation_result: res.investigation_result,
            customer_360: res.customer_360,
            requires_escalation: res.requires_escalation,
            escalation_dossier: res.escalation_dossier
          };
          setMessages((prev) => [...prev, assistantMsg]);
        }
      );
    } catch (err) {
      console.error('Chat error:', err);
      setAiState('ERROR');
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-5 h-full">
      {/* LEFT COLUMN: Conversation & Demo Launcher (5 cols) */}
      <div className="xl:col-span-5 flex flex-col h-[calc(100vh-8.5rem)] glass-standard rounded-2xl p-4">
        {/* Quick Demo Scenarios Launcher */}
        <DemoScenarioLauncher
          onRunScenario={(prompt, custId) => handleSend(prompt, custId)}
          disabled={aiState === 'EXECUTING'}
        />

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto pr-2 space-y-2">
          {messages.map((msg) => (
            <ChatMessageBubble key={msg.id} message={msg} />
          ))}

          {/* Typing / Thinking Indicator */}
          {(aiState === 'THINKING' || aiState === 'PLANNING' || aiState === 'EXECUTING') && (
            <div className="flex items-center gap-2 p-3 rounded-2xl glass-subtle text-xs text-cyan-300 font-mono animate-pulse w-fit">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-400" />
              <span>[{activeAgentName}]: Synthesizing actions & evaluating state...</span>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input Bar */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="mt-3 relative flex items-center"
        >
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={`Message AgentSupport AI (e.g. "Refund order ORD10002")...`}
            disabled={aiState === 'EXECUTING'}
            className="w-full pl-4 pr-12 py-3.5 rounded-xl bg-white/[0.04] border border-white/[0.12] focus:border-cyan-400/50 focus:bg-white/[0.07] focus:outline-none text-sm text-white placeholder-slate-400 transition-all font-sans"
          />
          <button
            type="submit"
            disabled={!inputText.trim() || aiState === 'EXECUTING'}
            className="absolute right-2 p-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-glow-cyan"
          >
            {aiState === 'EXECUTING' ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </form>
      </div>

      {/* CENTER COLUMN: AI Execution Panel & Spatial Graph (4 cols) */}
      <div className="xl:col-span-4 flex flex-col gap-4 overflow-y-auto h-[calc(100vh-8.5rem)] pr-1">
        {/* Active AI Task Panel with Investigation Findings */}
        <AIExecutionPanel
          goal={activeGoal}
          plan={activePlan}
          completedSteps={completedSteps}
          currentStep={currentStep}
          confidence={confidence}
          replanCount={replanCount}
          status={aiState}
          traceEvents={liveTraceEvents}
          investigationResult={investigationResult}
        />

        {/* Spatial Multi-Agent Graph */}
        <SpatialAgentGraph
          activeAgentName={activeAgentName}
          onSelectAgent={onSelectAgent}
          agents={agents}
        />
      </div>

      {/* RIGHT COLUMN: Customer 360 & Case Context Card (3 cols) */}
      <div className="xl:col-span-3 flex flex-col gap-4 overflow-y-auto h-[calc(100vh-8.5rem)]">
        <CustomerContextCard
          customer={currentCustomer}
          activeCaseId={activeCaseId}
          caseStatus={aiState === 'ESCALATED' ? 'ESCALATED' : aiState === 'COMPLETED' ? 'RESOLVED' : 'INVESTIGATING'}
          casePriority={investigationResult?.findings.some(f => f.impact === 'risk' || f.impact === 'blocker') ? 'high' : 'medium'}
          sentiment="frustrated"
        />
      </div>
    </div>
  );
};
