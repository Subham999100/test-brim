import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { User } from '../types';

const auth = vi.hoisted(() => ({ user: null as User | null }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: auth.user, loading: false }) }));

const { OrgAdminRoute, OrgRoute } = await import('./OrgRoutes');
const { ProtectedRoute } = await import('./ProtectedRoute');

const render = (node: ReactElement, path = '/app/organisation') =>
  renderToStaticMarkup(<MemoryRouter initialEntries={[path]}>{node}</MemoryRouter>);

const member: User = { id: 'm', email: 'm@x.com', name: 'M', account_type: 'organisation', org_role: 'member' };
const owner: User = { ...member, id: 'o', org_role: 'owner' };
const individual: User = { id: 'i', email: 'i@x.com', name: 'I', account_type: 'individual' };

describe('organisation route wrappers', () => {
  it('render the page only for the right accounts', () => {
    auth.user = member;
    expect(render(<OrgRoute><p>hub</p></OrgRoute>)).toBe('<p>hub</p>');
    expect(render(<OrgAdminRoute><p>admin</p></OrgAdminRoute>)).toBe('');

    auth.user = owner;
    expect(render(<OrgAdminRoute><p>admin</p></OrgAdminRoute>)).toBe('<p>admin</p>');

    auth.user = individual;
    expect(render(<OrgRoute><p>hub</p></OrgRoute>)).toBe('');
  });

  it('holds back every signed-in page while a password change is required', () => {
    auth.user = { ...member, must_change_password: true };
    expect(render(<ProtectedRoute><p>chat</p></ProtectedRoute>, '/app')).toBe('');
    expect(render(<ProtectedRoute><p>change</p></ProtectedRoute>, '/organisation/change-password')).toBe('<p>change</p>');
  });
});
