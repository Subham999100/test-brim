import React from 'react';
import { Navigate, useLocation, Link } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, LogIn } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AdminProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, token, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-white dark:bg-[#07090e] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-2 border-amber-500/20 border-t-amber-500 rounded-full animate-spin" />
          <span className="text-xs font-mono text-slate-600 dark:text-zinc-400">Verifying administrator authorization...</span>
        </div>
      </div>
    );
  }

  if (!token || !user) {
    return <Navigate to="/admin/login" state={{ from: location }} replace />;
  }

  if (!user.is_admin) {
    return (
      <div className="min-h-screen bg-white dark:bg-[#06080d] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white dark:bg-[#0d1117] border border-rose-500/30 rounded-2xl p-8 shadow-2xl text-center space-y-5">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-700 dark:text-rose-500 shadow-lg shadow-rose-500/10">
            <ShieldAlert size={34} />
          </div>

          <div className="space-y-2">
            <span className="inline-block px-3 py-1 rounded-full text-[11px] font-mono font-semibold uppercase tracking-wider bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20">
              403 Forbidden · Access Denied
            </span>
            <h1 className="text-xl font-bold text-slate-900 dark:text-white tracking-tight">
              Administrator Privileges Required
            </h1>
            <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
              Your account (<strong className="text-slate-800 dark:text-zinc-200">{user.email}</strong>) is authenticated as a standard user and does not possess Super Administrator permissions.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-amber-500/5 border border-amber-500/20 text-left text-xs text-amber-700/90 dark:text-amber-200/90 leading-relaxed">
            <span className="font-semibold block text-amber-700 dark:text-amber-300 mb-1">Administrative Policy</span>
            The Admin Dashboard, internal knowledge base sources, and document pipelines are strictly reserved for enterprise administrators.
          </div>

          <div className="flex flex-col sm:flex-row gap-2.5 pt-2">
            <Link
              to="/app"
              className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-slate-100 dark:bg-zinc-800 hover:bg-slate-100 dark:hover:bg-zinc-700 text-slate-800 dark:text-zinc-200 text-xs font-semibold transition"
            >
              <ArrowLeft size={14} /> Return to Workspace
            </Link>
            <button
              onClick={() => {
                logout();
                window.location.href = '/admin/login';
              }}
              className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-slate-950 text-xs font-bold transition shadow-md shadow-amber-500/20 cursor-pointer"
            >
              <LogIn size={14} /> Admin Sign In
            </button>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};
