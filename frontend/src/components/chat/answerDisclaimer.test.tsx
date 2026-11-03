import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { Message } from '../../types';

vi.mock('../../context/AuthContext', () => ({ useAuth: () => ({ user: null }) }));

const { ChatMessage } = await import('./ChatMessage');

const DISCLAIMER = 'Clyptus.AI can make mistakes.';

const answer = (overrides: Partial<Message> = {}): Message => ({
  id: '7f1c2a9e-0000-4000-8000-000000000002',
  chat_id: 'c1',
  role: 'assistant',
  content: 'Convergent Invoicing groups billable items into billing documents.',
  created_at: '2026-11-03T10:00:00Z',
  citations: [],
  web_sources: [],
  ...overrides,
});

const render = (message: Message, props: { onRegenerate?: () => void; isStreaming?: boolean } = {}) =>
  renderToStaticMarkup(
    <MemoryRouter>
      <ChatMessage message={message} {...props} />
    </MemoryRouter>,
  );

describe('answer disclaimer', () => {
  it('sits under the latest answer and points to Regenerate', () => {
    const html = render(answer(), { onRegenerate: () => {} });

    expect(html).toContain(DISCLAIMER);
    expect(html).toContain('If you think this answer is not correct, click');
    expect(html).toContain('Regenerate');
    expect(html.indexOf(DISCLAIMER)).toBeGreaterThan(html.indexOf('Convergent Invoicing'));
  });

  it('is not shown while the answer streams, on older answers without Regenerate, or on prompts', () => {
    expect(render(answer(), { onRegenerate: () => {}, isStreaming: true })).not.toContain(DISCLAIMER);
    expect(render(answer())).not.toContain(DISCLAIMER);
    expect(render(answer({ role: 'user' }), { onRegenerate: () => {} })).not.toContain(DISCLAIMER);
  });
});
