import React from 'react';
import { AIState } from '../../types';

interface Props {
  aiState: AIState;
}

export const AmbientBackground: React.FC<Props> = ({ aiState }) => {
  // Determine ambient light colors based on AI lifecycle state
  const getGlowStyles = () => {
    switch (aiState) {
      case 'THINKING':
      case 'PLANNING':
        return {
          glow1: 'from-cyan-500/20 to-blue-600/10',
          glow2: 'from-violet-600/15 to-transparent',
          glow3: 'from-teal-400/10 to-transparent',
        };
      case 'EXECUTING':
      case 'WAITING_FOR_TOOL':
        return {
          glow1: 'from-emerald-500/25 to-cyan-500/15',
          glow2: 'from-blue-600/20 to-transparent',
          glow3: 'from-teal-500/15 to-emerald-600/10',
        };
      case 'REPLANNING':
        return {
          glow1: 'from-amber-500/25 to-orange-600/15',
          glow2: 'from-yellow-500/15 to-transparent',
          glow3: 'from-rose-500/10 to-transparent',
        };
      case 'ESCALATED':
      case 'ERROR':
        return {
          glow1: 'from-rose-600/25 to-pink-600/15',
          glow2: 'from-amber-600/15 to-transparent',
          glow3: 'from-red-500/15 to-transparent',
        };
      case 'COMPLETED':
        return {
          glow1: 'from-emerald-500/20 to-cyan-500/15',
          glow2: 'from-teal-600/15 to-transparent',
          glow3: 'from-blue-500/10 to-transparent',
        };
      case 'IDLE':
      default:
        return {
          glow1: 'from-indigo-600/15 to-cyan-500/10',
          glow2: 'from-purple-900/15 to-transparent',
          glow3: 'from-blue-900/10 to-transparent',
        };
    }
  };

  const colors = getGlowStyles();

  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      {/* Deep Charcoal Base */}
      <div className="absolute inset-0 bg-[#08090C]" />

      {/* Floating Ambient Glow 1 */}
      <div
        className={`absolute -top-40 -left-40 w-[650px] h-[650px] rounded-full bg-gradient-to-br ${colors.glow1} blur-[120px] transition-all duration-1000 animate-ambient-glow`}
      />

      {/* Floating Ambient Glow 2 */}
      <div
        className={`absolute top-1/3 -right-40 w-[600px] h-[600px] rounded-full bg-gradient-to-bl ${colors.glow2} blur-[130px] transition-all duration-1000 animate-float-slow`}
      />

      {/* Floating Ambient Glow 3 */}
      <div
        className={`absolute -bottom-40 left-1/3 w-[700px] h-[500px] rounded-full bg-gradient-to-t ${colors.glow3} blur-[140px] transition-all duration-1000`}
      />

      {/* Subtle Noise / Grid Texture */}
      <div
        className="absolute inset-0 opacity-[0.025]"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, rgba(255,255,255,0.4) 1px, transparent 0)`,
          backgroundSize: '32px 32px'
        }}
      />
    </div>
  );
};
