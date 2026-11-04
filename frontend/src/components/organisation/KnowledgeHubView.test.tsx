import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { KnowledgeHubView, type KnowledgeHubViewProps } from './KnowledgeHubView';
import { likersSummary } from './orgFormat';
import type { KnowledgeCategory, OrgMe, SharedAnswerSummary } from '../../types';

const me: OrgMe = {
  organisation: { id: 'o1', name: 'Acme Telco', status: 'active', member_count: 12, created_at: '2026-10-01T10:00:00Z' },
  role: 'member',
  can_manage: false,
};

const categories: KnowledgeCategory[] = [
  { key: 'cc', label: 'Convergent Charging (CC)', count: 0 },
  { key: 'ci', label: 'Convergent Invoicing (CI)', count: 2 },
  { key: 'troubleshooting', label: 'Troubleshooting', count: 1 },
];

const items: SharedAnswerSummary[] = [
  {
    id: 'a1',
    question: 'Why are billable items stuck after the billing run?',
    answer_preview: 'Check the billable item class and the billing process settings first.',
    category: 'ci',
    category_label: 'Convergent Invoicing (CI)',
    shared_by_name: 'Priya Shah',
    created_at: '2026-10-30T12:00:00Z',
    like_count: 5,
    comment_count: 3,
    liked_by_me: true,
  },
  {
    id: 'a2',
    question: 'Invoice not generated for a contract account',
    answer_preview: 'Look at the invoicing run log.',
    category: 'troubleshooting',
    category_label: 'Troubleshooting',
    shared_by_name: 'Daniel Kim',
    created_at: '2026-10-29T12:00:00Z',
    like_count: 0,
    comment_count: 0,
    liked_by_me: false,
  },
];

const render = (overrides: Partial<KnowledgeHubViewProps> = {}) =>
  renderToStaticMarkup(
    <MemoryRouter>
      <KnowledgeHubView
        me={me}
        canManage={false}
        categories={categories}
        activeCategory=""
        onSelectCategory={() => {}}
        search=""
        onSearchChange={() => {}}
        items={items}
        total={2}
        error={null}
        onRetry={() => {}}
        onOpen={() => {}}
        onToggleLike={() => {}}
        likeBusyIds={new Set()}
        {...overrides}
      />
    </MemoryRouter>,
  );

describe('KnowledgeHubView', () => {
  it('shows the organisation header with role and member count', () => {
    const html = render();
    expect(html).toContain('<h1>Acme Telco</h1>');
    expect(html).toContain('Member');
    expect(html).toContain('12 members');
    expect(html).not.toContain('Admin dashboard');
  });

  it('lists topics with counts, All topics first and selected', () => {
    const html = render();
    expect(html).toMatch(/aria-current="true"[^>]*><span>All topics<\/span><span class="org-topic-count">3<\/span>/);
    expect(html).toMatch(/<span>Convergent Invoicing \(CI\)<\/span><span class="org-topic-count">2<\/span>/);
    expect(html).toMatch(/<span>Convergent Charging \(CC\)<\/span><span class="org-topic-count">0<\/span>/);
  });

  it('renders answer cards with sharer, counts and the liked-by-me state', () => {
    const html = render();
    expect(html).toContain('Why are billable items stuck after the billing run?');
    expect(html).toContain('Check the billable item class');
    expect(html).toContain('Shared by Priya Shah');
    expect(html).toContain('aria-pressed="true" aria-label="Unlike this answer, 5 likes"');
    expect(html).toContain('aria-pressed="false" aria-label="Like this answer, 0 likes"');
    expect(html).toContain('aria-label="Open comments, 3 comments"');
    expect(html).toContain('2 answers');
  });

  it('teaches how to share when the hub is empty', () => {
    const html = render({ items: [], total: 0 });
    expect(html).toContain('No shared answers yet');
    // One click: the "Org" button or Share; no like needed (owner request 2026-11-04).
    expect(html).toContain('<strong>Org</strong>');
    expect(html).toContain('<strong>Share to Knowledge Hub</strong>');
    expect(html).not.toContain('thumbs-up');
    expect(html).not.toContain('Share to organisation');
    expect(html).toContain('href="/app"');
  });

  it('offers to clear filters when a search finds nothing', () => {
    const html = render({ items: [], total: 0, search: 'dunning' });
    expect(html).toContain('No matching answers');
    expect(html).not.toContain('No shared answers yet');
  });

  it('links organisation admins to the admin dashboard', () => {
    expect(render({ canManage: true })).toMatch(/href="\/app\/organisation\/admin"[^>]*>.*?Admin dashboard/);
  });

  it('shows loading placeholders and errors', () => {
    expect(render({ items: null })).toContain('aria-busy="true"');
    expect(render({ items: null, error: 'Could not load shared answers.' })).toMatch(/role="alert"/);
  });
});

describe('likersSummary', () => {
  it('names the first likers and counts the rest', () => {
    expect(likersSummary([])).toBe('No likes yet');
    expect(likersSummary(['Priya'])).toBe('Liked by Priya');
    expect(likersSummary(['Priya', 'Daniel'])).toBe('Liked by Priya and Daniel');
    expect(likersSummary(['Priya', 'Daniel', 'Ana', 'Lee'])).toBe('Liked by Priya, Daniel and 2 others');
  });
});
