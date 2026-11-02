import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { User } from '../types';

const auth = vi.hoisted(() => ({ user: null as User | null }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: auth.user, logout: vi.fn() }) }));
vi.mock('../services/projectService', () => ({ projectService: { getProjects: () => [] } }));

const { AppLayout } = await import('./AppLayout');

const organisationHref = (user: User) => {
  auth.user = user;
  const html = renderToStaticMarkup(
    <MemoryRouter initialEntries={['/app/settings']}>
      <AppLayout />
    </MemoryRouter>,
  );
  return [...html.matchAll(/<a[^>]*href="([^"]*)"[^>]*>(?:(?!<\/a>).)*>Organisation<\/span><\/a>/g)].map(([, href]) => href);
};

describe('AppLayout sidebar Organisation item', () => {
  it('sends individual users to the public Organisation Portal', () => {
    expect(organisationHref({ id: 'i', email: 'i@x.com', name: 'I', account_type: 'individual' })).toEqual(['/organisation']);
  });

  it('sends organisation users to their knowledge hub', () => {
    expect(
      organisationHref({ id: 'm', email: 'm@x.com', name: 'M', account_type: 'organisation', org_role: 'member' }),
    ).toEqual(['/app/organisation']);
  });
});
