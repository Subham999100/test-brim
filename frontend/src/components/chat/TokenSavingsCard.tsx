import React from 'react';
import { Leaf } from 'lucide-react';
import type { TokenSavingsSummary } from '../../types';
import { TOKEN_ESTIMATE_NOTE, accountSavingsText } from './tokenSavings';

export type TokenSavingsState =
  | { status: 'loading' }
  | { status: 'error' }
  | { status: 'ready'; summary: TokenSavingsSummary };

const textFor = (state: TokenSavingsState): { headline: string; detail: string } => {
  if (state.status === 'ready') return accountSavingsText(state.summary);
  if (state.status === 'error') return { headline: 'Token savings', detail: 'Your total is not available right now.' };
  return { headline: 'Token savings', detail: 'Loading your total…' };
};

/** Settings: the estimated tokens saved across all of the user's answers. */
export const TokenSavingsCard: React.FC<{ state: TokenSavingsState }> = ({ state }) => {
  const { headline, detail } = textFor(state);
  return (
    <div className="settings-group">
      <div className="settings-group-heading">
        <h2>Token savings</h2>
        <p>Estimated against an AI chatbot that resends the whole conversation with every question.</p>
      </div>
      <div className="settings-row" title={TOKEN_ESTIMATE_NOTE}>
        <div className="settings-row-icon">
          <span className="account-avatar" aria-hidden="true">
            <Leaf size={14} />
          </span>
        </div>
        <div>
          <strong className="tabular-nums">{headline}</strong>
          <span>{detail}</span>
        </div>
      </div>
    </div>
  );
};
