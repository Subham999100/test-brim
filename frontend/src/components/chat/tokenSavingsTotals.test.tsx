import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import type { Message } from '../../types';
import { ChatSavingsLine } from './ChatSavingsLine';
import { TokenSavingsCard } from './TokenSavingsCard';
import { accountSavingsText, chatSavings } from './tokenSavings';

const message = (role: 'user' | 'assistant', saved?: number): Message => ({
  id: `${role}-${Math.random()}`,
  chat_id: 'c1',
  role,
  content: '…',
  created_at: '2026-11-04T10:00:00Z',
  citations: [],
  web_sources: [],
  ...(saved === undefined ? {} : { token_usage: { used: 100, baseline: 100 + saved, saved } }),
});

describe('chatSavings', () => {
  it('adds up the stored savings of the answers in this chat', () => {
    const messages = [message('user'), message('assistant', 1200), message('user'), message('assistant', 2200)];
    expect(chatSavings(messages)).toBe(3400);
  });

  it('ignores prompts and answers without stored figures', () => {
    expect(chatSavings([message('user', 999), message('assistant'), message('assistant', 0)])).toBe(0);
  });
});

describe('ChatSavingsLine', () => {
  it('shows the saving for the whole chat', () => {
    const html = renderToStaticMarkup(<ChatSavingsLine messages={[message('assistant', 3400)]} />);
    expect(html).toContain('~3,400 tokens saved in this chat');
    expect(html).toContain('title="Estimated at about 4 characters per token.');
  });

  it('shows nothing until something was saved', () => {
    expect(renderToStaticMarkup(<ChatSavingsLine messages={[message('assistant', 0)]} />)).toBe('');
    expect(renderToStaticMarkup(<ChatSavingsLine messages={[]} />)).toBe('');
  });
});

describe('accountSavingsText', () => {
  it('summarises the saving and compares it with other AI chatbots', () => {
    expect(accountSavingsText({ answers: 31, used: 29_500, baseline: 77_700, saved: 48_200 })).toEqual({
      headline: '~48,200 tokens saved',
      detail: 'Across 31 answers · 62% fewer tokens than other AI chatbots would use.',
    });
  });

  it('uses the singular for one answer', () => {
    expect(accountSavingsText({ answers: 1, used: 10, baseline: 40, saved: 30 }).detail).toMatch(/^Across 1 answer ·/);
  });

  it('never shows 0 as a saving', () => {
    expect(accountSavingsText({ answers: 0, used: 0, baseline: 0, saved: 0 })).toEqual({
      headline: 'No tokens saved yet',
      detail: 'Your savings appear here after your first answers.',
    });
    expect(accountSavingsText({ answers: 4, used: 900, baseline: 800, saved: 0 }).headline).toBe('No tokens saved yet');
  });
});

describe('TokenSavingsCard', () => {
  it('renders the account total in the Settings style', () => {
    const html = renderToStaticMarkup(
      <TokenSavingsCard state={{ status: 'ready', summary: { answers: 31, used: 29_500, baseline: 77_700, saved: 48_200 } }} />,
    );
    expect(html).toContain('<h2>Token savings</h2>');
    expect(html).toContain('~48,200 tokens saved');
    expect(html).toContain('62% fewer tokens');
  });

  it('says so when the total cannot be loaded', () => {
    expect(renderToStaticMarkup(<TokenSavingsCard state={{ status: 'error' }} />)).toContain('not available right now');
    expect(renderToStaticMarkup(<TokenSavingsCard state={{ status: 'loading' }} />)).toContain('Loading');
  });
});
