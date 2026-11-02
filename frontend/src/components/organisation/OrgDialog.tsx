import React, { useId, useRef } from 'react';
import { AlertTriangle, Loader2, X } from 'lucide-react';
import { useDialog } from './useDialog';

/**
 * Accessible modal: role="dialog" + aria-modal, labelled by its title, Escape and backdrop click close it,
 * Tab stays inside, focus moves in on open and returns to the opener on close.
 */
export function OrgModal({
  title,
  description,
  onClose,
  children,
  wide = false,
}: {
  title: string;
  description?: React.ReactNode;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  const titleId = useId();
  const descriptionId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  useDialog(panelRef, onClose);

  return (
    <div
      className="org-modal-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className={`org-modal${wide ? ' org-modal-wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
      >
        <div className="org-modal-head">
          <h2 id={titleId}>{title}</h2>
          <button type="button" className="org-icon-btn" onClick={onClose} aria-label="Close dialog">
            <X size={17} aria-hidden="true" />
          </button>
        </div>
        {description && (
          <div id={descriptionId} className="org-modal-description">
            {description}
          </div>
        )}
        <div className="org-modal-body">{children}</div>
      </div>
    </div>
  );
}

/** Confirmation step for destructive or hard-to-undo actions. */
export function ConfirmDialog({
  title,
  message,
  confirmLabel,
  tone = 'danger',
  busy = false,
  error,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: React.ReactNode;
  confirmLabel: string;
  tone?: 'danger' | 'default';
  busy?: boolean;
  error?: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <OrgModal title={title} onClose={busy ? () => undefined : onCancel}>
      <div className="org-confirm">
        {tone === 'danger' && (
          <span className="org-confirm-icon" aria-hidden="true">
            <AlertTriangle size={18} />
          </span>
        )}
        <div className="org-confirm-message">{message}</div>
      </div>
      {error && (
        <p className="org-alert" role="alert">
          {error}
        </p>
      )}
      <div className="org-modal-actions">
        <button type="button" className="org-btn org-btn-ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button
          type="button"
          className={`org-btn ${tone === 'danger' ? 'org-btn-danger' : 'org-btn-primary'}`}
          onClick={onConfirm}
          disabled={busy}
        >
          {busy && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
          {confirmLabel}
        </button>
      </div>
    </OrgModal>
  );
}
