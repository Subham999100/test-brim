import React, { useState } from 'react';
import { AlertCircle, ArrowRight, KeyRound } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { PageMeta } from '../../components/ui/PageMeta';
import { OrgAuthLayout } from '../../components/organisation/OrgAuthLayout';
import { ActivationAccountForm } from '../../components/organisation/ActivationAccountForm';
import { formatActivationCode, validateActivationCode } from '../../components/organisation/orgFormat';
import { useAuth } from '../../context/AuthContext';
import { ACTIVATION_CODE_INVALID, apiOrgCompleteActivation, apiOrgVerifyActivation } from '../../services/api';
import { ORG_ADMIN_PATH, ORG_LOGIN_PATH } from '../../layouts/accountRouting';
import type { ActivationCodeDetails } from '../../types';

/** Activation: verify the Super-Admin-issued code, then create the owner account and sign in. */
export const OrgActivatePage: React.FC = () => {
  const { applySession } = useAuth();
  const navigate = useNavigate();

  const [code, setCode] = useState('');
  const [details, setDetails] = useState<ActivationCodeDetails | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const step = details ? 2 : 1;

  const handleVerify = async (event: React.FormEvent) => {
    event.preventDefault();
    const problem = validateActivationCode(code);
    setError(problem);
    if (problem) return;
    const formatted = formatActivationCode(code);
    setCode(formatted);
    setBusy(true);
    try {
      setDetails(await apiOrgVerifyActivation(formatted));
    } catch (err) {
      setError(err instanceof Error ? err.message : ACTIVATION_CODE_INVALID);
    } finally {
      setBusy(false);
    }
  };

  const handleComplete = async (name: string, password: string) => {
    setError(null);
    setBusy(true);
    try {
      const session = await apiOrgCompleteActivation(formatActivationCode(code), name, password);
      applySession(session);
      navigate(ORG_ADMIN_PATH, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : ACTIVATION_CODE_INVALID);
      setBusy(false);
    }
  };

  return (
    <>
      <PageMeta title="Activate Organisation" description="Activate your Clyptus.AI organisation workspace with your activation code." />
      <OrgAuthLayout
        quote="“Activation codes are single-use and time-limited, so only the administrator you nominated can set up your workspace.”"
        caption="Issued by Clyptus · Verified on our servers"
      >
        <span className="eyebrow">ORGANISATION ACTIVATION</span>
        <h1>{step === 1 ? 'Activate your organisation' : 'Set up your admin account'}</h1>
        <p>
          {step === 1
            ? 'Enter the activation code you received from your Clyptus administrator.'
            : 'You will be the owner of this organisation workspace.'}
        </p>

        <ol className="org-steps" aria-label="Activation progress">
          <li aria-current={step === 1 ? 'step' : undefined} className={step > 1 ? 'done' : undefined}>
            <span aria-hidden="true">1</span> Verify code
          </li>
          <li aria-current={step === 2 ? 'step' : undefined}>
            <span aria-hidden="true">2</span> Admin account
          </li>
        </ol>

        {step === 1 && (
          <>
            {error && (
              <div className="auth-error" role="alert">
                <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
                <span>{error}</span>
              </div>
            )}
            <form className="auth-form" onSubmit={handleVerify} noValidate>
              <div className="auth-field">
                <label htmlFor="org-activation-code">Activation code</label>
                <div className="auth-input org-code-input">
                  <KeyRound aria-hidden="true" />
                  <input
                    id="org-activation-code"
                    type="text"
                    required
                    autoComplete="one-time-code"
                    autoCapitalize="characters"
                    spellCheck={false}
                    maxLength={40}
                    aria-describedby="org-activation-code-hint"
                    value={code}
                    onChange={(e) => setCode(e.target.value)}
                    onBlur={() => code.trim() && setCode(formatActivationCode(code))}
                    placeholder="CLY-XXXX-XXXX-XXXX-XXXX"
                  />
                </div>
                <small id="org-activation-code-hint" className="auth-hint">
                  Codes are single-use and expire. Spaces and hyphens are optional.
                </small>
              </div>
              <button type="submit" disabled={busy} className="button button-brand auth-submit">
                <span>{busy ? 'Verifying…' : 'Verify code'}</span>
                <ArrowRight size={15} aria-hidden="true" />
              </button>
            </form>
          </>
        )}

        {step === 2 && details && (
          <ActivationAccountForm
            details={details}
            submitting={busy}
            error={error}
            onSubmit={handleComplete}
            onBack={() => {
              setDetails(null);
              setError(null);
            }}
          />
        )}

        <div className="org-auth-links">
          <span>
            Already activated? <Link to={ORG_LOGIN_PATH}>Sign in to your organisation</Link>
          </span>
          <span>
            No code yet? <Link to="/organisation#request">Request an organisation account</Link>
          </span>
        </div>
      </OrgAuthLayout>
    </>
  );
};
