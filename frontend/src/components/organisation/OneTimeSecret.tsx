import React, { useState } from 'react';
import { AlertTriangle, Check, Copy } from 'lucide-react';
import { copyText, formatDateTime } from './orgFormat';

/**
 * Shows a secret the server returns exactly once (temporary password, activation code) with a copy
 * button and a clear warning. The value is kept only in component state and never stored.
 */
export function OneTimeSecret({
  label,
  value,
  expiresAt,
  children,
}: {
  label: string;
  value: string;
  expiresAt?: string | null;
  children?: React.ReactNode;
}) {
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');

  const copy = async () => {
    const ok = await copyText(value);
    setCopyState(ok ? 'copied' : 'failed');
    if (ok) window.setTimeout(() => setCopyState('idle'), 2500);
  };

  return (
    <div className="org-secret">
      <span className="org-secret-label">{label}</span>
      <div className="org-secret-row">
        <code className="org-secret-value" aria-label={label}>
          {value}
        </code>
        <button type="button" className="org-btn org-btn-primary org-btn-sm" onClick={copy} aria-label={`Copy ${label.toLowerCase()}`}>
          {copyState === 'copied' ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
          {copyState === 'copied' ? 'Copied' : 'Copy'}
        </button>
      </div>
      {copyState === 'failed' && (
        <p className="org-secret-hint" role="alert">
          Copying is blocked in this browser. Select the value and copy it manually.
        </p>
      )}
      {expiresAt && <p className="org-secret-hint">Expires {formatDateTime(expiresAt)}.</p>}
      <div className="org-warning" role="note">
        <AlertTriangle size={16} aria-hidden="true" />
        <p>
          <strong>Shown only once.</strong> Copy it now and share it securely; it cannot be displayed again.
          {children && <> {children}</>}
        </p>
      </div>
    </div>
  );
}
