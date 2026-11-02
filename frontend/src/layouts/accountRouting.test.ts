import { describe, expect, it } from 'vitest';
import {
  isOrgAdmin,
  isOrgUser,
  orgAdminRouteDecision,
  organisationNavTarget,
  orgRouteDecision,
  postSignInPath,
  protectedRouteDecision,
  signInPathFor,
} from './accountRouting';
import type { User } from '../types';

const individual: User = { id: 'u1', email: 'a@x.com', name: 'A', account_type: 'individual' };
const legacy: User = { id: 'u0', email: 'l@x.com', name: 'Legacy' }; // older server: no account_type
const member: User = { id: 'u2', email: 'm@x.com', name: 'M', account_type: 'organisation', org_role: 'member' };
const admin: User = { ...member, id: 'u3', org_role: 'admin' };
const owner: User = { ...member, id: 'u4', org_role: 'owner' };
const mustChange: User = { ...member, id: 'u5', must_change_password: true };

describe('account type helpers', () => {
  it('recognises organisation accounts and their admins', () => {
    expect([individual, legacy, null].map(isOrgUser)).toEqual([false, false, false]);
    expect([member, admin, owner].map(isOrgUser)).toEqual([true, true, true]);
    expect([member, admin, owner, individual].map(isOrgAdmin)).toEqual([false, true, true, false]);
  });

  it('sends the sidebar Organisation item to the portal or the knowledge hub', () => {
    expect(organisationNavTarget(individual)).toBe('/organisation');
    expect(organisationNavTarget(legacy)).toBe('/organisation');
    expect(organisationNavTarget(member)).toBe('/app/organisation');
    expect(organisationNavTarget(owner)).toBe('/app/organisation');
  });

  it('lands users after sign-in by account type and pending password change', () => {
    expect(postSignInPath(individual)).toBe('/app');
    expect(postSignInPath(member)).toBe('/app/organisation');
    expect(postSignInPath(mustChange)).toBe('/organisation/change-password');
  });

  it('picks the matching sign-in page when a session ends', () => {
    expect(signInPathFor('/admin')).toBe('/admin/login');
    expect(signInPathFor('/app/organisation')).toBe('/organisation/login');
    expect(signInPathFor('/app/chat/1', 'organisation')).toBe('/organisation/login');
    expect(signInPathFor('/app/chat/1', 'individual')).toBe('/login');
  });
});

describe('route guards', () => {
  it('sends signed-out users to the right sign-in page', () => {
    expect(protectedRouteDecision(null, '/app')).toEqual({ kind: 'redirect', to: '/login' });
    expect(protectedRouteDecision(null, '/app/organisation')).toEqual({ kind: 'redirect', to: '/organisation/login' });
  });

  it('allows only the change-password page until a temporary password is replaced', () => {
    expect(protectedRouteDecision(mustChange, '/app')).toEqual({ kind: 'redirect', to: '/organisation/change-password' });
    expect(protectedRouteDecision(mustChange, '/app/organisation')).toEqual({
      kind: 'redirect',
      to: '/organisation/change-password',
    });
    expect(protectedRouteDecision(mustChange, '/organisation/change-password')).toEqual({ kind: 'allow' });
    expect(protectedRouteDecision(member, '/app/organisation')).toEqual({ kind: 'allow' });
  });

  it('keeps individual users out of organisation routes', () => {
    expect(orgRouteDecision(individual)).toEqual({ kind: 'redirect', to: '/organisation' });
    expect(orgRouteDecision(member)).toEqual({ kind: 'allow' });
  });

  it('opens the organisation admin dashboard to owners and admins only', () => {
    expect(orgAdminRouteDecision(individual)).toEqual({ kind: 'redirect', to: '/organisation' });
    expect(orgAdminRouteDecision(member)).toEqual({ kind: 'redirect', to: '/app/organisation' });
    expect(orgAdminRouteDecision(admin)).toEqual({ kind: 'allow' });
    expect(orgAdminRouteDecision(owner)).toEqual({ kind: 'allow' });
  });
});
