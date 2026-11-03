import React from 'react';
import { Zap } from 'lucide-react';
import type { TokenUsage } from '../../types';
import { TOKEN_ESTIMATE_NOTE, tokensLabel, useCountUp } from './tokenSavings';

interface TokenMeterBadgeProps {
  /** True while the answer streams. */
  streaming?: boolean;
  /** Final figures once the answer is complete. */
  usage?: TokenUsage;
}

const badgeClass =
  'inline-flex items-center gap-1.5 shrink-0 px-2.5 py-0.5 rounded-full text-[11px] font-medium border shadow-sm select-none bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/50';

/** Answer header badge opposite "Clyptus.AI": the tokens saved, never the tokens used. */
export const TokenMeterBadge: React.FC<TokenMeterBadgeProps> = ({ streaming = false, usage }) => {
  const saved = usage?.saved ?? 0;
  // Runs up when the answer completes; starts at 1 so a saving is never shown as 0.
  const shown = useCountUp(saved, Math.min(1, saved));

  if (saved > 0) {
    return (
      <span title={TOKEN_ESTIMATE_NOTE} aria-label={`Saved ${tokensLabel(saved)}`} className={badgeClass}>
        <span aria-hidden="true">😊</span>
        <span aria-hidden="true" className="tabular-nums font-semibold">Saved {tokensLabel(shown)}</span>
      </span>
    );
  }
  if (streaming) {
    return (
      <span title={TOKEN_ESTIMATE_NOTE} className={badgeClass}>
        <span aria-hidden="true">😊</span>
        <Zap className="w-3 h-3 text-orange-500 animate-pulse" aria-hidden="true" />
        <span>Saving tokens…</span>
      </span>
    );
  }
  return null;
};
