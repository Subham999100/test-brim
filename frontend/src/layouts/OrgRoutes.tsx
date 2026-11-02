import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { orgAdminRouteDecision, orgRouteDecision, type RouteDecision } from './accountRouting';

// Used inside ProtectedRoute, so the user is already signed in and has no pending password change.

function Guarded({ decision, children }: { decision: RouteDecision; children: React.ReactElement }) {
  return decision.kind === 'redirect' ? <Navigate to={decision.to} replace /> : children;
}

/** Organisation accounts only; individual users are sent to the public Organisation Portal. */
export function OrgRoute({ children }: { children: React.ReactElement }) {
  const { user } = useAuth();
  return <Guarded decision={orgRouteDecision(user)}>{children}</Guarded>;
}

/** Organisation owners and admins only; members are sent to the knowledge hub. */
export function OrgAdminRoute({ children }: { children: React.ReactElement }) {
  const { user } = useAuth();
  return <Guarded decision={orgAdminRouteDecision(user)}>{children}</Guarded>;
}
