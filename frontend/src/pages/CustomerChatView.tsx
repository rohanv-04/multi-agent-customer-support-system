import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Loader2, User, Phone, X, ShieldCheck, CheckCircle2 } from 'lucide-react';
import { ChatMessage, Customer, TraceEvent, AIState, AgentInfo, InvestigationResult } from '../types';
import { ChatMessageBubble } from '../components/chat/ChatMessageBubble';
import { AIExecutionPanel } from '../components/chat/AIExecutionPanel';
import { SpatialAgentGraph } from '../components/chat/SpatialAgentGraph';
import { CustomerContextCard } from '../components/chat/CustomerContextCard';
import { DemoScenarioLauncher } from '../components/chat/DemoScenarioLauncher';
import { HumanSupportCard } from '../components/chat/HumanSupportCard';
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
        "Hi! I'm SupportOS AI, your autonomous customer support assistant for NovaCart. I can check order statuses, review policies, investigate delays, and resolve account issues. How can I help you today?",
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
  const [showHumanDrawer, setShowHumanDrawer] = useState<boolean>(false);

  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, liveTraceEvents, aiState]);

  const getTypingStatusText = () => {
    const agent = activeAgentName.toLowerCase();
    if (agent.includes('shipping') || currentStep.toLowerCase().includes('order') || currentStep.toLowerCase().includes('track')) {
      return 'AI is checking order & shipping records...';
    }
    if (agent.includes('policy') || currentStep.toLowerCase().includes('policy')) {
      return 'AI is reviewing relevant policy terms...';
    }
    if (agent.includes('refund') || currentStep.toLowerCase().includes('refund')) {
      return 'AI is evaluating refund eligibility...';
    }
    if (agent.includes('resolution') || agent.includes('tool')) {
      return 'AI is investigating live business data...';
    }
    if (agent.includes('critic') || agent.includes('valid')) {
      return 'AI is validating resolution details...';
    }
    return 'AI is analyzing your request...';
  };

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
      {/* LEFT COLUMN: Conversational AI Support Interface (5 cols) */}
      <div className="xl:col-span-5 flex flex-col h-[calc(100vh-8.5rem)] glass-standard rounded-2xl p-4 relative overflow-hidden">
        {/* Chat Header with Status & Persistent Human Button in Corner */}
        <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-200 dark:border-white/[0.08]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-cyan-500/20 border border-cyan-400/30 flex items-center justify-center text-cyan-600 dark:text-cyan-300">
              <Sparkles className="w-4 h-4 text-cyan-500 dark:text-cyan-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold text-slate-900 dark:text-white tracking-wide">SupportOS AI</h2>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              </div>
              <p className="text-[10px] text-slate-500 dark:text-slate-400">Autonomous Customer Operations</p>
            </div>
          </div>

          {/* Persistent Human Escape Hatch Button in Top Corner */}
          <button
            onClick={() => setShowHumanDrawer(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-100/90 dark:bg-white/[0.05] hover:bg-slate-200 dark:hover:bg-white/[0.12] border border-slate-200 dark:border-white/[0.12] hover:border-cyan-400/40 text-[11px] font-medium text-slate-700 dark:text-slate-300 hover:text-cyan-700 dark:hover:text-cyan-300 transition-all group shadow-sm"
            title="Speak with a dedicated support representative"
          >
            <User className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400 group-hover:scale-110 transition-transform" />
            <span>👤 Speak with Human</span>
          </button>
        </div>

        {/* Quick Demo Scenarios Launcher */}
        <DemoScenarioLauncher
          onRunScenario={(prompt, custId) => handleSend(prompt, custId)}
          disabled={aiState === 'EXECUTING'}
        />

        {/* Message Thread */}
        <div className="flex-1 overflow-y-auto pr-2 space-y-1">
          {messages.map((msg) => (
            <ChatMessageBubble
              key={msg.id}
              message={msg}
              onConnectHuman={() => setShowHumanDrawer(true)}
            />
          ))}

          {/* Natural Typing / Investigating Indicator */}
          {(aiState === 'THINKING' || aiState === 'PLANNING' || aiState === 'EXECUTING' || aiState === 'VALIDATING') && (
            <div className="flex items-center gap-2.5 p-3 rounded-2xl bg-slate-100/90 dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.08] text-xs text-cyan-700 dark:text-cyan-300 font-sans animate-pulse w-fit my-2">
              <Loader2 className="w-3.5 h-3.5 animate-spin text-cyan-600 dark:text-cyan-400 shrink-0" />
              <span>{getTypingStatusText()}</span>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Persistent Input Bar with Corner Human Option */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="mt-3 relative flex items-center gap-2"
        >
          <div className="relative flex-1">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Type your message naturally..."
              disabled={aiState === 'EXECUTING'}
              className="w-full pl-4 pr-12 py-3.5 rounded-xl bg-slate-100/90 dark:bg-white/[0.04] border border-slate-200 dark:border-white/[0.12] focus:border-cyan-500 focus:bg-white dark:focus:bg-white/[0.07] focus:outline-none text-sm text-slate-900 dark:text-white placeholder-slate-400 transition-all font-sans"
            />
            <button
              type="submit"
              disabled={!inputText.trim() || aiState === 'EXECUTING'}
              className="absolute right-2 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-glow-cyan"
            >
              {aiState === 'EXECUTING' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Corner Human Escalate Button */}
          <button
            type="button"
            onClick={() => setShowHumanDrawer(true)}
            className="p-3.5 rounded-xl bg-slate-100/90 dark:bg-white/[0.04] hover:bg-slate-200 dark:hover:bg-white/[0.08] border border-slate-200 dark:border-white/[0.12] hover:border-cyan-400/40 text-slate-700 dark:text-slate-300 hover:text-cyan-700 dark:hover:text-cyan-300 transition-all flex items-center justify-center shrink-0 shadow-sm"
            title="Talk to a Human Agent"
          >
            <User className="w-4 h-4" />
          </button>
        </form>

        {/* Slide-over Drawer / Modal for Human Support */}
        {showHumanDrawer && (
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-md p-4 z-50 flex flex-col justify-end animate-fadeIn">
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-white/[0.1]">
              <div className="flex items-center gap-2 text-xs font-bold text-white uppercase tracking-wider">
                <User className="w-4 h-4 text-cyan-400" />
                <span>Human Support Desk</span>
              </div>
              <button
                onClick={() => setShowHumanDrawer(false)}
                className="p-1 rounded-lg hover:bg-white/10 text-slate-400 hover:text-white transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <HumanSupportCard
              caseId={activeCaseId}
              customerId={currentCustomer?.customer_id || 'CUST1002'}
              onAssigned={() => {
                if (onTicketCreated) onTicketCreated();
              }}
            />
          </div>
        )}
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

      {/* RIGHT COLUMN: Customer 360 & Context Panel (3 cols) */}
      <div className="xl:col-span-3 flex flex-col gap-4 overflow-y-auto h-[calc(100vh-8.5rem)]">
        <HumanSupportCard
          caseId={activeCaseId}
          customerId={currentCustomer?.customer_id || 'CUST1002'}
          onAssigned={() => {
            if (onTicketCreated) onTicketCreated();
          }}
        />

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
