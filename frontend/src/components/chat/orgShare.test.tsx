import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { Message, User } from '../../types';
import { orgShareState } from './orgShare';

const auth = vi.hoisted(() => ({ user: null as User | null }));
vi.mock('../../context/AuthContext', () => ({ useAuth: () => ({ user: auth.user }) }));

const { ChatMessage } = await import('./ChatMessage');

const orgUser: User = { id: 'u1', email: 'm@acme.example', name: 'M', account_type: 'organisation', org_role: 'member' };
const individual: User = { id: 'u2', email: 'i@x.com', name: 'I', account_type: 'individual' };

const answer = (overrides: Partial<Message> = {}): Message => ({
  id: '7f1c2a9e-0000-4000-8000-000000000001',
  chat_id: 'c1',
  role: 'assistant',
  content: 'Convergent Invoicing groups billable items into billing documents.',
  created_at: '2026-11-01T10:00:00Z',
  citations: [],
  web_sources: [],
  ...overrides,
});

describe('orgShareState', () => {
  it('offers sharing only to organisation users on a liked, stored answer', () => {
    expect(orgShareState({ user: orgUser, message: answer(), feedback: 'up' })).toBe('share');
    expect(orgShareState({ user: orgUser, message: answer(), feedback: null })).toBe('hidden');
    expect(orgShareState({ user: orgUser, message: answer(), feedback: 'down' })).toBe('hidden');
    expect(orgShareState({ user: individual, message: answer(), feedback: 'up' })).toBe('hidden');
    expect(orgShareState({ user: null, message: answer(), feedback: 'up' })).toBe('hidden');
  });

  it('never offers prompts, unsaved, streaming or failed answers', () => {
    expect(orgShareState({ user: orgUser, message: answer({ role: 'user' }), feedback: 'up' })).toBe('hidden');
    expect(orgShareState({ user: orgUser, message: answer({ id: 'err-1' }), feedback: 'up' })).toBe('hidden');
    expect(orgShareState({ user: orgUser, message: answer(), feedback: 'up', isStreaming: true })).toBe('hidden');
    expect(orgShareState({ user: orgUser, message: answer({ source_type: 'error' }), feedback: 'up' })).toBe('hidden');
  });

  it('shows Shared for answers already in the hub, liked or not', () => {
    const sharedIds = new Set([answer().id]);
    expect(orgShareState({ user: orgUser, message: answer(), feedback: 'up', sharedIds })).toBe('shared');
    expect(orgShareState({ user: orgUser, message: answer(), feedback: null, sharedIds })).toBe('shared');
    expect(orgShareState({ user: individual, message: answer(), feedback: 'up', sharedIds })).toBe('hidden');
  });
});

describe('ChatMessage organisation sharing', () => {
  const render = (user: User, message: Message, sharedIds?: ReadonlySet<string>) => {
    auth.user = user;
    return renderToStaticMarkup(
      <MemoryRouter>
        <ChatMessage message={message} orgSharedIds={sharedIds} />
      </MemoryRouter>,
    );
  };

  it('shows Share to organisation under a liked answer for organisation users', () => {
    const html = render(orgUser, answer({ feedback: 'up' }));
    expect(html).toContain('Share to organisation');
    expect(html).not.toContain('View in Knowledge Hub');
  });

  it('hides it until the answer is liked, and for individual users', () => {
    expect(render(orgUser, answer({ feedback: null }))).not.toContain('Share to organisation');
    expect(render(individual, answer({ feedback: 'up' }))).not.toContain('Share to organisation');
  });

  it('shows Shared with a hub link for answers already shared', () => {
    const html = render(orgUser, answer({ feedback: 'up' }), new Set([answer().id]));
    expect(html).toContain('Shared');
    expect(html).toContain('href="/app/organisation"');
    expect(html).not.toContain('Share to organisation');
  });
});
