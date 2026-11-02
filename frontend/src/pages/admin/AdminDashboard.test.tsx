import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'admin-1', email: 'admin@clyptus.example', name: 'Admin', is_admin: true }, logout: vi.fn() }),
}));
// The document manager has its own data loading; it is not part of this test.
vi.mock('../DocumentManagementPage', () => ({ DocumentManagementPage: () => <div>documents tab</div> }));

const { AdminDashboard } = await import('./AdminDashboard');

const html = renderToStaticMarkup(
  <MemoryRouter initialEntries={['/admin']}>
    <AdminDashboard />
  </MemoryRouter>,
);

const tabLabels = [...html.matchAll(/<button type="button" aria-pressed="(true|false)"[^>]*>.*?<span>([^<]+)<\/span><\/button>/g)].map(
  ([, pressed, label]) => ({ label, pressed: pressed === 'true' }),
);

describe('AdminDashboard account management tabs', () => {
  it('puts Organisations and Individual users first, as separate tabs', () => {
    expect(tabLabels.map((t) => t.label)).toEqual([
      'Organisations',
      'Individual users',
      'Document Manager &amp; Ingestion',
      'Internal Sources &amp; Repository',
      'Retrieval &amp; Chunk Sandbox',
      'System &amp; Security Policy',
    ]);
    expect(html.indexOf('Accounts')).toBeLessThan(html.indexOf('>Organisations<'));
    expect(html.indexOf('Knowledge base')).toBeGreaterThan(html.indexOf('>Individual users<'));
  });

  it('opens on Organisation Management only, not the individual user list', () => {
    expect(tabLabels.filter((t) => t.pressed).map((t) => t.label)).toEqual(['Organisations']);
    expect(html).toContain('Organisation Management');
    expect(html).toContain('Create organisation');
    expect(html).not.toContain('Individual User Management');
    expect(html).not.toContain('documents tab');
  });

  it('offers the status filter for organisations', () => {
    for (const status of ['All', 'Requested', 'Pending activation', 'Active', 'Suspended', 'Deactivated', 'Rejected']) {
      expect(html).toMatch(new RegExp(`aria-pressed="(true|false)">${status}</button>`));
    }
  });
});
