import React, { useState, useEffect } from 'react';
import { ListTodo, CheckCircle2, AlertTriangle, RefreshCw, Clock, Wrench, ChevronRight } from 'lucide-react';
import { getTasks, getTaskDetail } from '../services/api';

export const TasksView: React.FC = () => {
  const [tasks, setTasks] = useState<any[]>([]);
  const [selectedTask, setSelectedTask] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchTasks = async () => {
    try {
      const data = await getTasks();
      setTasks(data);
      if (data.length > 0 && !selectedTask) {
        loadTaskDetail(data[0].task_id);
      }
    } catch (e) {
      console.error('Error fetching tasks:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadTaskDetail = async (taskId: string) => {
    try {
      const detail = await getTaskDetail(taskId);
      setSelectedTask(detail);
    } catch (e) {
      console.error('Error fetching task detail:', e);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'escalated':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      case 'replanning':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      default:
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-10">
      <div className="glass-elevated rounded-3xl p-6 sm:p-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-2xl bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 shadow-glow-cyan">
            <ListTodo className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-white">Task State History & Explorer</h2>
            <p className="text-xs text-slate-400 font-mono">
              Audit log of autonomous goal decomposition, step progress, & real tool executions
            </p>
          </div>
        </div>

        <button
          onClick={fetchTasks}
          className="p-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 border border-white/[0.1] transition-all flex items-center gap-1.5 text-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Tasks List (5 cols) */}
        <div className="lg:col-span-5 space-y-2.5 max-h-[calc(100vh-16rem)] overflow-y-auto pr-1">
          {tasks.length === 0 ? (
            <div className="glass-standard rounded-2xl p-8 text-center text-xs text-slate-400">
              No tasks recorded in database yet.
            </div>
          ) : (
            tasks.map((t) => {
              const isSelected = selectedTask?.task_id === t.task_id;
              return (
                <div
                  key={t.task_id}
                  onClick={() => loadTaskDetail(t.task_id)}
                  className={`glass-standard p-4 rounded-2xl cursor-pointer transition-all ${
                    isSelected
                      ? 'border-cyan-400/50 bg-cyan-500/10 shadow-glow-cyan'
                      : 'hover:border-white/20'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-[11px] font-bold text-slate-300">{t.task_id}</span>
                    <span className={`px-2 py-0.5 rounded-full text-[9px] font-semibold border ${getStatusBadge(t.status)}`}>
                      {t.status.toUpperCase()}
                    </span>
                  </div>

                  <p className="text-xs font-medium text-white line-clamp-2 mb-2">{t.user_goal}</p>

                  <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                    <span>Customer: {t.customer_id}</span>
                    <span>Conf: {Math.round(t.confidence * 100)}%</span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Selected Task Details (7 cols) */}
        <div className="lg:col-span-7">
          {selectedTask ? (
            <div className="glass-standard rounded-2xl p-6 space-y-5">
              <div className="flex items-start justify-between border-b border-white/[0.08] pb-4">
                <div>
                  <span className="text-[10px] font-mono text-cyan-400 uppercase tracking-wider block mb-1">
                    Task Inspector: {selectedTask.task_id}
                  </span>
                  <h3 className="text-lg font-bold text-white leading-snug">
                    {selectedTask.user_goal}
                  </h3>
                </div>

                <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusBadge(selectedTask.status)}`}>
                  {selectedTask.status.toUpperCase()}
                </span>
              </div>

              {/* Steps Timeline */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3">
                  Step-by-Step DAG Execution ({selectedTask.steps?.length || 0})
                </h4>

                <div className="space-y-2">
                  {selectedTask.steps?.map((step: any) => (
                    <div
                      key={step.step_number}
                      className="p-3 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-start gap-3 text-xs"
                    >
                      <span className="w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 flex items-center justify-center font-mono text-[10px] shrink-0 mt-0.5">
                        {step.step_number}
                      </span>
                      <span className="text-slate-200 leading-snug">{step.description}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Tool Calls Executed */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 flex items-center gap-1.5">
                  <Wrench className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Real Tool Invocations ({selectedTask.tool_calls?.length || 0})</span>
                </h4>

                <div className="space-y-2">
                  {selectedTask.tool_calls?.length === 0 ? (
                    <p className="text-xs text-slate-400 italic">No tool calls recorded for this task.</p>
                  ) : (
                    selectedTask.tool_calls.map((tc: any, i: number) => (
                      <div
                        key={i}
                        className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.06] flex items-center justify-between text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-cyan-300">{tc.tool_name}</span>
                          <span className={`px-2 py-0.5 rounded text-[9px] font-mono ${tc.status === 'success' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                            {tc.status}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-400 font-mono">{tc.duration_ms}ms</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="glass-standard rounded-2xl p-12 text-center text-xs text-slate-400">
              Select a task from the left to inspect its detailed state.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
