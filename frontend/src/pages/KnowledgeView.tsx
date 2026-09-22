import React, { useState, useEffect } from 'react';
import { BookOpen, RefreshCw, Search, FileText, CheckCircle2, Layers } from 'lucide-react';
import { getKnowledgeDocs, reindexKnowledge, searchKnowledge } from '../services/api';

export const KnowledgeView: React.FC = () => {
  const [docs, setDocs] = useState<any[]>([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [query, setQuery] = useState('');
  const [searchResults, setSearchResults] = useState<any | null>(null);
  const [searching, setSearching] = useState(false);
  const [reindexing, setReindexing] = useState(false);

  const fetchDocs = async () => {
    try {
      const data = await getKnowledgeDocs();
      setDocs(data.documents || []);
      setTotalChunks(data.total_chunks || 0);
    } catch (e) {
      console.error('Error fetching knowledge docs:', e);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleReindex = async () => {
    setReindexing(true);
    try {
      const res = await reindexKnowledge();
      await fetchDocs();
      alert(`Re-indexed successfully! ${res.chunk_count} policy chunks ready.`);
    } catch (e) {
      console.error('Error re-indexing:', e);
    } finally {
      setReindexing(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setSearching(true);
    try {
      const res = await searchKnowledge(query);
      setSearchResults(res);
    } catch (e) {
      console.error('Error searching:', e);
    } finally {
      setSearching(false);
    }
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-10">
      <div className="glass-elevated rounded-3xl p-6 sm:p-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 shadow-glow-cyan">
            <BookOpen className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Knowledge Base & RAG Engine</h2>
            <p className="text-xs text-slate-400 font-mono">
              Indexed NovaCart Corporate Policies (TF-IDF & Cosine Similarity Embeddings)
            </p>
          </div>
        </div>

        <button
          onClick={handleReindex}
          disabled={reindexing}
          className="px-4 py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-200 border border-white/[0.1] transition-all flex items-center gap-2 text-xs font-mono disabled:opacity-40"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${reindexing ? 'animate-spin' : ''}`} />
          <span>{reindexing ? 'Re-Indexing Chunks...' : `Re-Index (${totalChunks} Chunks)`}</span>
        </button>
      </div>

      {/* Semantic Search Tester */}
      <div className="glass-standard rounded-2xl p-6">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-2">
          <Search className="w-4 h-4 text-cyan-400" />
          <span>Interactive RAG Semantic Search Tester</span>
        </h3>

        <form onSubmit={handleSearch} className="flex gap-3 mb-4">
          <input
            type="text"
            placeholder="Type a policy question (e.g. 'What is the refund rule for delayed shipments?')..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 px-4 py-3 rounded-xl bg-white/[0.04] border border-white/[0.1] text-sm text-white placeholder-slate-400 focus:outline-none focus:border-cyan-400"
          />
          <button
            type="submit"
            disabled={searching || !query.trim()}
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-xs font-semibold hover:opacity-90 disabled:opacity-40 transition-all shadow-glow-cyan"
          >
            {searching ? 'Querying...' : 'Search RAG'}
          </button>
        </form>

        {searchResults && (
          <div className="mt-4 p-4 rounded-xl bg-black/40 border border-white/[0.08] space-y-3">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-300">
                Found {searchResults.citations?.length || 0} Grounded Policy Excerpts
              </span>
              <span className="text-cyan-300 font-bold">
                Confidence: {Math.round(searchResults.confidence * 100)}%
              </span>
            </div>

            <div className="text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-wrap bg-white/[0.02] p-3 rounded-lg border border-white/[0.05]">
              {searchResults.combined_context}
            </div>
          </div>
        )}
      </div>

      {/* Indexed Document Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {docs.map((d) => (
          <div key={d.doc_id} className="glass-standard p-5 rounded-2xl space-y-2">
            <div className="flex items-center justify-between">
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
                {d.category}
              </span>
              <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                <Layers className="w-3 h-3 text-cyan-400" />
                {d.chunk_count} Chunks
              </span>
            </div>

            <h4 className="text-sm font-bold text-white leading-snug">{d.title}</h4>
            <p className="text-[11px] text-slate-400 font-mono">{d.filename}</p>

            <div className="pt-2 border-t border-white/[0.06] flex items-center justify-between text-[10px] text-emerald-400">
              <span className="flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Indexed & Ready
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
