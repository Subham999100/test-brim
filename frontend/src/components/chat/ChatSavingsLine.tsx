import React from 'react';
import type { Message } from '../../types';
import { TOKEN_ESTIMATE_NOTE, chatSavings, tokensLabel } from './tokenSavings';

/** A quiet line above the conversation: the tokens saved by this chat's answers so far. */
export const ChatSavingsLine: React.FC<{ messages: Message[] }> = ({ messages }) => {
  const saved = chatSavings(messages);
  if (saved <= 0) return null;
  return (
    <p
      title={TOKEN_ESTIMATE_NOTE}
      className="mx-auto mt-3 mb-1 w-fit px-3 py-1 rounded-full text-[11px] font-medium tabular-nums select-none border bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800/50"
    >
      <span aria-hidden="true">😊 </span>
      {`${tokensLabel(saved)} saved in this chat`}
    </p>
  );
};
