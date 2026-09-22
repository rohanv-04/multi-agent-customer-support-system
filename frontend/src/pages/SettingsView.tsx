import React, { useState } from 'react';
import { Settings, Sliders, ShieldCheck, Key, Cpu, Save } from 'lucide-react';

export const SettingsView: React.FC = () => {
  const [provider, setProvider] = useState('local');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('gpt-4o-mini');
  const [confidenceThreshold, setConfidenceThreshold] = useState(75);
  const [maxReplans, setMaxReplans] = useState(5);
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-10">
      <div className="glass-elevated rounded-3xl p-6 sm:p-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2.5 rounded-2xl bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 shadow-glow-cyan">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">System & Model Configuration</h2>
            <p className="text-xs text-slate-400 font-mono">
              LLM Provider Abstraction, Confidence Gateways, & Re-planning Loop Limits
            </p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSave} className="glass-standard rounded-2xl p-6 space-y-6">
        {/* LLM Engine Selection */}
        <div>
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-300 block mb-2">
            LLM Provider & Orchestration Mode
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setProvider('local')}
              className={`p-4 rounded-xl border text-left transition-all ${
                provider === 'local'
                  ? 'bg-cyan-500/15 border-cyan-400 text-white shadow-glow-cyan'
                  : 'bg-white/[0.03] border-white/[0.08] text-slate-400'
              }`}
            >
              <div className="font-bold text-sm text-cyan-300 mb-1">Local Deterministic Engine</div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Zero-setup offline agentic execution. Uses exact rule-guided LangGraph state transitions, tool execution, and RAG retrieval.
              </p>
            </button>

            <button
              type="button"
              onClick={() => setProvider('openai')}
              className={`p-4 rounded-xl border text-left transition-all ${
                provider === 'openai'
                  ? 'bg-cyan-500/15 border-cyan-400 text-white shadow-glow-cyan'
                  : 'bg-white/[0.03] border-white/[0.08] text-slate-400'
              }`}
            >
              <div className="font-bold text-sm text-cyan-300 mb-1">OpenAI / Compatible Cloud API</div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Direct integration with GPT-4o, Groq, or OpenRouter via universal OpenAI client.
              </p>
            </button>
          </div>
        </div>

        {/* API Key & Model inputs */}
        {provider === 'openai' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
            <div>
              <label className="text-xs text-slate-400 block mb-1.5 font-mono">API Key</label>
              <input
                type="password"
                placeholder="sk-..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-cyan-400"
              />
            </div>

            <div>
              <label className="text-xs text-slate-400 block mb-1.5 font-mono">Model Identifier</label>
              <input
                type="text"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/[0.1] text-xs text-white focus:outline-none focus:border-cyan-400 font-mono"
              />
            </div>
          </div>
        )}

        {/* Confidence Threshold Slider */}
        <div className="pt-2">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Critic Agent Confidence Threshold: <span className="text-cyan-300 font-mono">{confidenceThreshold}%</span>
            </label>
            <span className="text-[10px] text-slate-400 font-mono">Default: 75%</span>
          </div>
          <input
            type="range"
            min="50"
            max="95"
            value={confidenceThreshold}
            onChange={(e) => setConfidenceThreshold(Number(e.target.value))}
            className="w-full h-1.5 bg-white/[0.1] rounded-lg appearance-none cursor-pointer accent-cyan-400"
          />
          <p className="text-[11px] text-slate-400 mt-1">
            Tasks evaluating below this threshold are redirected by the Critic Agent to the Re-planning loop or escalated to a human specialist.
          </p>
        </div>

        {/* Max Re-plans Slider */}
        <div className="pt-2">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Maximum Re-Planning Loops: <span className="text-amber-300 font-mono">{maxReplans} iterations</span>
            </label>
            <span className="text-[10px] text-slate-400 font-mono">Guarded against infinite cycles</span>
          </div>
          <input
            type="range"
            min="1"
            max="8"
            value={maxReplans}
            onChange={(e) => setMaxReplans(Number(e.target.value))}
            className="w-full h-1.5 bg-white/[0.1] rounded-lg appearance-none cursor-pointer accent-amber-400"
          />
        </div>

        <div className="pt-4 flex items-center justify-between border-t border-white/[0.08]">
          <span className="text-xs text-emerald-400 font-mono">
            {saved ? '✓ Settings saved successfully!' : ''}
          </span>
          <button
            type="submit"
            className="px-6 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-semibold hover:opacity-90 transition-all shadow-glow-cyan flex items-center gap-2"
          >
            <Save className="w-3.5 h-3.5" />
            <span>Save Configuration</span>
          </button>
        </div>
      </form>
    </div>
  );
};
