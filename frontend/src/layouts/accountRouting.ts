import type { User } from '../types';

// Routing rules for individual and organisation accounts (docs/ORGANISATION_PORTAL.md, "Frontend routes").
// Pure functions so the guards, sidebar and sign-in pages share one tested source of truth.

export const ORG_PORTAL_PATH = '/organisation';
export const ORG_LOGIN_PATH = '/organisation/login';
export const ORG_ACTIVATE_PATH = '/organisation/activate';
export const ORG_CHANGE_PASSWORD_PATH = '/organisation/change-password';
export const ORG_HUB_PATH = '/app/organisation';
export const ORG_ADMIN_PATH = '/app/organisation/admin';

type MaybeUser = Pick<User, 'account_type' | 'org_role' | 'must_change_password'> | null | undefined;

export const isOrgUser = (user: MaybeUser): boolean => user?.account_type === 'organisation';

export const isOrgAdmin = (user: MaybeUser): boolean =>
  isOrgUser(user) && (user?.org_role === 'owner' || user?.org_role === 'admin');

/** Where the sidebar "Organisation" item leads. */
export const organisationNavTarget = (user: MaybeUser): string => (isOrgUser(user) ? ORG_HUB_PATH : ORG_PORTAL_PATH);

/** Where a user lands after signing in. */
export const postSignInPath = (user: MaybeUser): string => {
  if (user?.must_change_password) return ORG_CHANGE_PASSWORD_PATH;
  return isOrgUser(user) ? ORG_HUB_PATH : '/app';
};

/** Which sign-in page to send someone to when their session ends. */
export const signInPathFor = (pathname: string, accountType?: string | null): string => {
  if (pathname.startsWith('/admin')) return '/admin/login';
  if (accountType === 'organisation' || pathname.startsWith(ORG_PORTAL_PATH) || pathname.startsWith(ORG_HUB_PATH)) {
    return ORG_LOGIN_PATH;
  }
  return '/login';
};

export type RouteDecision = { kind: 'allow' } | { kind: 'redirect'; to: string };

const allow: RouteDecision = { kind: 'allow' };
const redirect = (to: string): RouteDecision => ({ kind: 'redirect', to });

/** Any signed-in route. Users who must change their password can reach only the change-password page. */
export const protectedRouteDecision = (user: MaybeUser, pathname: string): RouteDecision => {
  if (!user) return redirect(signInPathFor(pathname));
  if (user.must_change_password && pathname !== ORG_CHANGE_PASSWORD_PATH) return redirect(ORG_CHANGE_PASSWORD_PATH);
  return allow;
};

/** Organisation-only routes: individual users are sent to the public Organisation Portal. */
export const orgRouteDecision = (user: MaybeUser): RouteDecision =>
  isOrgUser(user) ? allow : redirect(ORG_PORTAL_PATH);

/** Organisation admin routes: owners and admins only; members go to the knowledge hub. */
export const orgAdminRouteDecision = (user: MaybeUser): RouteDecision => {
  if (!isOrgUser(user)) return redirect(ORG_PORTAL_PATH);
  return isOrgAdmin(user) ? allow : redirect(ORG_HUB_PATH);
};
