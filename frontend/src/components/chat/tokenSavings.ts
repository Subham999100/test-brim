import { useEffect, useRef, useState } from 'react';
import type { TokenUsage } from '../../types';

/** Shown on hover: how the saving is estimated and what it is compared with. */
export const TOKEN_ESTIMATE_NOTE =
  'Estimated at about 4 characters per token. A typical AI chatbot resends the whole conversation and every ' +
  'matching passage with each question; Clyptus.AI sends only the best passages and a short summary.';

export const formatTokens = (tokens: number): string => Math.max(0, Math.round(tokens)).toLocaleString('en-US');

export const tokensLabel = (tokens: number): string =>
  `~${formatTokens(tokens)} ${Math.round(tokens) === 1 ? 'token' : 'tokens'}`;

export interface SavingsMessage {
  saved: boolean;
  emoji: string;
  title: string;
  detail: string;
}

/** What the popup says after every answer. A saving is never shown as 0: no saving gets its own wording. */
export const savingsMessage = (usage: TokenUsage): SavingsMessage => {
  if (usage.saved > 0) {
    const percent = usage.baseline > 0 ? Math.max(1, Math.round((usage.saved / usage.baseline) * 100)) : 0;
    return {
      saved: true,
      emoji: '😊',
      title: `You saved ${tokensLabel(usage.saved)}!`,
      detail: percent
        ? `That's ${percent}% fewer than other AI chatbots would use for this question.`
        : 'Fewer than other AI chatbots would use for this question.',
    };
  }
  return {
    saved: false,
    emoji: '😅',
    title: 'No tokens saved for this question.',
    detail: 'Savings grow as your conversation gets longer.',
  };
};

/** Counts smoothly from `initial` (then from the last shown value) to `target`, so the number runs up. */
export const useCountUp = (target: number, initial = target, durationMs = 900): number => {
  const [value, setValue] = useState(initial);
  const valueRef = useRef(initial);

  useEffect(() => {
    const from = valueRef.current;
    if (from === target) return;
    const start = performance.now();
    let frame = 0;
    const step = (now: number) => {
      const progress = Math.min(1, (now - start) / durationMs);
      const next = Math.round(from + (target - from) * (1 - (1 - progress) ** 3));
      valueRef.current = next;
      setValue(next);
      if (progress < 1) frame = requestAnimationFrame(step);
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, durationMs]);

  return value;
};
