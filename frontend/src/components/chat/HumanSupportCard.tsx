import React, { useState, useEffect } from 'react';
import { User, Phone, CheckCircle2, Loader2, Sparkles, AlertCircle } from 'lucide-react';
import { HumanSupportAssignment } from '../../types';
import { requestHumanSupport, recordCallInitiated, getHumanSupportAssignment } from '../../services/api';

interface Props {
  caseId: string | null;
  customerId?: string;
  onAssigned?: (assignment: HumanSupportAssignment) => void;
  className?: string;
}

export const HumanSupportCard: React.FC<Props> = ({
  caseId,
  customerId = 'CUST1002',
  onAssigned,
  className = ''
}) => {
  const [assignment, setAssignment] = useState<HumanSupportAssignment | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isCalling, setIsCalling] = useState<boolean>(false);
  const [callInitiated, setCallInitiated] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Check if case already has an active assignment
  useEffect(() => {
    if (caseId) {
      getHumanSupportAssignment(caseId)
        .then((data) => {
          if (data) {
            setAssignment(data);
            if (data.status === 'CALL_INITIATED') {
              setCallInitiated(true);
            }
          }
        })
        .catch(() => {});
    }
  }, [caseId]);

  const handleRequestHuman = async () => {
    setIsLoading(true);
    setError(null);
    const targetCaseId = caseId || `CASE-${Date.now().toString().slice(-6)}`;

    try {
      const res = await requestHumanSupport(targetCaseId, customerId);
      setAssignment(res);
      if (onAssigned) onAssigned(res);
    } catch (err: any) {
      console.error('Human support assignment error:', err);
      setError('Unable to assign representative at this moment. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCallNow = async () => {
    if (!assignment) return;
    setIsCalling(true);

    try {
      // 1. Open device phone dialer
      window.location.href = assignment.tel_link || `tel:${assignment.representative.phone}`;

      // 2. Record CALL_INITIATED in backend
      await recordCallInitiated(assignment.case_id, assignment.assignment_id);
      setCallInitiated(true);
    } catch (err) {
      console.error('Record call initiated error:', err);
      // Even if logging fails, dialer was opened
      setCallInitiated(true);
    } finally {
      setIsCalling(false);
    }
  };

  return (
    <div className={`p-4 rounded-2xl glass-standard space-y-3 shadow-lg ${className}`}>
      {!assignment ? (
        // Initial state: One primary option to speak with a human agent
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-cyan-700 dark:text-cyan-300 font-semibold text-xs uppercase tracking-wider font-mono">
            <User className="w-4 h-4 text-cyan-600 dark:text-cyan-400" />
            <span>Human Support</span>
          </div>

          <div className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
            Need help from a human agent? We will connect you directly with a dedicated support specialist from our team.
          </div>

          {error && (
            <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-700 dark:text-rose-300 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <button
            onClick={handleRequestHuman}
            disabled={isLoading}
            className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white text-xs font-bold shadow-md shadow-cyan-500/20 flex items-center justify-center gap-2 transition-all disabled:opacity-50 group"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Connecting with team...</span>
              </>
            ) : (
              <>
                <User className="w-4 h-4 group-hover:scale-110 transition-transform" />
                <span>👤 Speak with a Human Agent</span>
              </>
            )}
          </button>
        </div>
      ) : (
        // Assigned state: Displays selected representative & Call Now button
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400 font-semibold text-xs uppercase tracking-wider font-mono">
              <CheckCircle2 className="w-4 h-4" />
              <span>Human Agent Assigned</span>
            </div>
            <span className="text-[10px] font-mono text-cyan-700 dark:text-cyan-300 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
              #{assignment.assignment_id}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-100/90 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 space-y-1 text-center">
            <div className="text-[11px] text-slate-500 dark:text-slate-400">You have been connected to:</div>
            <div className="text-lg font-extrabold text-slate-900 dark:text-white tracking-wide">
              {assignment.representative.name}
            </div>
            <div className="text-[11px] text-cyan-700 dark:text-cyan-400 font-mono">
              Dedicated Support Representative
            </div>
          </div>

          <div className="space-y-2">
            <a
              href={assignment.tel_link || `tel:${assignment.representative.phone}`}
              onClick={handleCallNow}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-white text-xs font-bold shadow-md shadow-emerald-500/20 flex items-center justify-center gap-2 transition-all"
            >
              <Phone className="w-4 h-4" />
              <span>📞 Call Now</span>
            </a>

            {callInitiated ? (
              <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-center text-[10px] font-mono text-emerald-700 dark:text-emerald-300">
                ✓ Call link opened on device (CALL_INITIATED)
              </div>
            ) : (
              <div className="text-[10px] text-center text-slate-500 dark:text-slate-400 font-mono">
                Clicking will open your phone dialer with representative's direct number.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
