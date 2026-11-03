import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import type { TokenUsage } from '../../types';
import { savingsMessage } from './tokenSavings';

const VISIBLE_MS = 6000;

interface TokenSavedToastProps {
  /** Figures of the answer that just completed; null hides the popup. Shown for every answer. */
  usage: TokenUsage | null;
  onClose: () => void;
}

/** Popup after every answer: the tokens saved compared with other AI chatbots, or that none were saved. */
export const TokenSavedToast: React.FC<TokenSavedToastProps> = ({ usage, onClose }) => {
  // `onClose` must be stable (useCallback), or every parent render restarts the timer.
  useEffect(() => {
    if (!usage) return;
    const timer = setTimeout(onClose, VISIBLE_MS);
    return () => clearTimeout(timer);
  }, [usage, onClose]);

  if (!usage) return null;
  const message = savingsMessage(usage);

  return (
    <div
      role="status"
      className={`fixed z-50 bottom-28 left-4 right-4 sm:left-auto sm:right-6 sm:w-96 flex items-start gap-3 rounded-2xl border px-4 py-3 shadow-2xl backdrop-blur-md animate-[modal-enter_.25s_ease-out] ${
        message.saved
          ? 'bg-emerald-50/95 dark:bg-emerald-950/90 border-emerald-200 dark:border-emerald-800/60 text-emerald-900 dark:text-emerald-100'
          : 'bg-slate-50/95 dark:bg-slate-900/90 border-slate-200 dark:border-slate-700/60 text-slate-800 dark:text-slate-100'
      }`}
    >
      <span className="text-2xl leading-none" aria-hidden="true">{message.emoji}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold">{message.title}</p>
        <p className="mt-0.5 text-xs opacity-80">{message.detail}</p>
      </div>
      <button
        type="button"
        onClick={onClose}
        aria-label="Close"
        className="p-1 -m-1 rounded-lg opacity-60 hover:opacity-100 transition cursor-pointer"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
};
