import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { Message, User } from '../../types';
import { orgShareState } from './orgShare';

const auth = vi.hoisted(() => ({ user: null as User | null }));
vi.mock('../../context/AuthContext', () => ({ useAuth: () => ({ user: auth.user }) }));

const { ChatMessage } = await import('./ChatMessage');
const { SharePromptModal } = await import('./SharePromptModal');

const orgUser: User = { id: 'u1', email: 'm@acme.example', name: 'M', account_type: 'organisation', org_role: 'member' };
const individual: User = { id: 'u2', email: 'i@x.com', name: 'I', account_type: 'individual' };

const ORG_BUTTON = 'aria-label="Share with your organisation"';
// The colour and underline sit on a span inside the link: index.css a{color:inherit;text-decoration:none}
// is outside any layer and beats Tailwind utilities on the <a> itself (KNOWN_ISSUES UI-001).
const HUB_LINK = /href="\/app\/organisation"[^>]*><span class="[^"]*\btext-emerald-700\b[^"]*\bunderline\b[^"]*">View in Knowledge Hub</;

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
  it('offers sharing to organisation users on any stored answer, liked or not', () => {
    expect(orgShareState({ user: orgUser, message: answer() })).toBe('share');
    expect(orgShareState({ user: orgUser, message: answer({ feedback: 'down' }) })).toBe('share');
    expect(orgShareState({ user: individual, message: answer() })).toBe('hidden');
    expect(orgShareState({ user: null, message: answer() })).toBe('hidden');
  });

  it('never offers prompts, unsaved, streaming or failed answers', () => {
    expect(orgShareState({ user: orgUser, message: answer({ role: 'user' }) })).toBe('hidden');
    expect(orgShareState({ user: orgUser, message: answer({ id: 'err-1' }) })).toBe('hidden');
    expect(orgShareState({ user: orgUser, message: answer(), isStreaming: true })).toBe('hidden');
    expect(orgShareState({ user: orgUser, message: answer({ source_type: 'error' }) })).toBe('hidden');
  });

  it('shows Shared for answers already in the hub', () => {
    const sharedIds = new Set([answer().id]);
    expect(orgShareState({ user: orgUser, message: answer(), sharedIds })).toBe('shared');
    expect(orgShareState({ user: individual, message: answer(), sharedIds })).toBe('hidden');
  });
});

describe('ChatMessage organisation sharing', () => {
  const render = (user: User, message: Message, options: { sharedIds?: ReadonlySet<string>; regenerate?: boolean } = {}) => {
    auth.user = user;
    return renderToStaticMarkup(
      <MemoryRouter>
        <ChatMessage
          message={message}
          orgSharedIds={options.sharedIds}
          onRegenerate={options.regenerate === false ? undefined : () => {}}
        />
      </MemoryRouter>,
    );
  };

  it('puts a one-click Org button right after Regenerate, without needing a like', () => {
    const html = render(orgUser, answer({ feedback: null }));
    expect(html).toContain(ORG_BUTTON);
    expect(html).toMatch(/aria-label="Share with your organisation"[^>]*>[\s\S]*?Org<\/span><\/button>/);
    expect(html.indexOf('aria-label="Regenerate response"')).toBeLessThan(html.indexOf(ORG_BUTTON));
  });

  it('keeps the Org button on older answers that cannot be regenerated', () => {
    expect(render(orgUser, answer(), { regenerate: false })).toContain(ORG_BUTTON);
  });

  it('shows no Org button to individual users', () => {
    expect(render(individual, answer({ feedback: 'up' }))).not.toContain(ORG_BUTTON);
  });

  it('turns into Shared with a hub link once the answer is in the hub', () => {
    const html = render(orgUser, answer(), { sharedIds: new Set([answer().id]) });
    expect(html).not.toContain(ORG_BUTTON);
    expect(html).toContain('aria-label="Shared with your organisation"');
    expect(html).toMatch(HUB_LINK);
  });

  it('no longer shows the old like-gated button under the answer', () => {
    expect(render(orgUser, answer({ feedback: 'up' }))).not.toContain('Share to organisation');
  });
});

describe('Share dialog organisation section', () => {
  const render = (organisation?: { shared: boolean; sharing: boolean; error: string | null }) =>
    renderToStaticMarkup(
      <MemoryRouter>
        <SharePromptModal
          chatId="c1"
          messageId="m1"
          prompt="An answer"
          isAnswer
          onClose={() => {}}
          organisation={organisation && { ...organisation, onShare: () => {} }}
        />
      </MemoryRouter>,
    );

  it('lets organisation users share the answer to the Knowledge Hub', () => {
    const html = render({ shared: false, sharing: false, error: null });
    expect(html).toContain('Share with your organisation');
    expect(html).toMatch(/<button[^>]*>[\s\S]*?Share to Knowledge Hub[\s\S]*?<\/button>/);
    expect(html).not.toContain('View in Knowledge Hub');
  });

  it('shows the shared state with a hub link, and any error', () => {
    const shared = render({ shared: true, sharing: false, error: null });
    expect(shared).toMatch(HUB_LINK);
    expect(shared).not.toContain('Share to Knowledge Hub');
    expect(render({ shared: false, sharing: false, error: 'Could not share this answer.' })).toMatch(
      /role="alert"[^>]*>Could not share this answer\./,
    );
  });

  it('has no organisation section for other users', () => {
    expect(render()).not.toContain('Share with your organisation');
  });
});
