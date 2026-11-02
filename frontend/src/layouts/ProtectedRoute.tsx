import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { protectedRouteDecision } from './accountRouting';

export function ProtectedRoute({
  children,
}: {
  children: React.ReactElement;
}) {
  const location = useLocation();
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="route-loading" role="status">
        Connecting to Clyptusap.ai...
      </div>
    );
  }

  // Signed-out users go to the matching sign-in page; users with a temporary password must change it first.
  const decision = protectedRouteDecision(user, location.pathname);
  if (decision.kind === 'redirect') {
    return <Navigate to={decision.to} replace state={{ from: location.pathname }} />;
  }

  return children;
}
