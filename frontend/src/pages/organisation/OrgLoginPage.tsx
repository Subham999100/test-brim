import React, { useEffect, useState } from 'react';
import { AlertCircle, ArrowRight, Eye, EyeOff, Lock, Mail } from 'lucide-react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { PageMeta } from '../../components/ui/PageMeta';
import { OrgAuthLayout } from '../../components/organisation/OrgAuthLayout';
import { useAuth } from '../../context/AuthContext';
import { ORG_ACTIVATE_PATH, postSignInPath } from '../../layouts/accountRouting';

/** Organisation sign-in (POST /org/auth/login). Individual accounts are told to use /login. */
export const OrgLoginPage: React.FC = () => {
  const { user, orgLogin } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(() =>
    searchParams.get('expired') ? 'Your session has expired. Please sign in again.' : null,
  );

  // Already signed in: go where this account belongs.
  useEffect(() => {
    if (user) navigate(postSignInPath(user), { replace: true });
  }, [user, navigate]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const signedIn = await orgLogin(email.trim(), password);
      navigate(postSignInPath(signedIn), { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-in failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <PageMeta title="Organisation Sign In" description="Sign in to your Clyptus.AI organisation workspace." />
      <OrgAuthLayout>
        <span className="eyebrow">ORGANISATION PORTAL</span>
        <h1>Sign in to your organisation</h1>
        <p>Use the email and password your organisation administrator gave you.</p>

        {error && (
          <div className="auth-error" role="alert">
            <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="auth-field">
            <label htmlFor="org-login-email">Work email</label>
            <div className="auth-input">
              <Mail aria-hidden="true" />
              <input
                id="org-login-email"
                type="email"
                required
                autoComplete="username"
                inputMode="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
              />
            </div>
          </div>

          <div className="auth-field">
            <label htmlFor="org-login-password">Password</label>
            <div className="auth-input">
              <Lock aria-hidden="true" />
              <input
                id="org-login-password"
                type={showPassword ? 'text' : 'password'}
                required
                maxLength={72}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Your password"
              />
              <button
                type="button"
                className="auth-reveal"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                aria-pressed={showPassword}
              >
                {showPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={loading} className="button button-brand auth-submit">
            <span>{loading ? 'Signing in…' : 'Sign in'}</span>
            <ArrowRight size={15} aria-hidden="true" />
          </button>
        </form>

        <div className="org-auth-links">
          <span>
            Received an activation code? <Link to={ORG_ACTIVATE_PATH}>Activate your organisation</Link>
          </span>
          <span>
            Using Clyptus.AI on your own? <Link to="/login">Sign in with an individual account</Link>
          </span>
        </div>
      </OrgAuthLayout>
    </>
  );
};
