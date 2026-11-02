import React, { useState } from 'react';
import { AlertCircle, ArrowRight, Building2, CheckCircle2, Mail, User } from 'lucide-react';
import { apiOrgSubmitRequest } from '../../services/api';
import { isValidEmail } from './orgFormat';
import { REQUEST_SUCCESS_MESSAGE } from './portalContent';

const MESSAGE_MAX = 1000;

/** Public "Request an organisation account" form (POST /org/requests). */
export function OrgRequestForm() {
  const [organisationName, setOrganisationName] = useState('');
  const [contactName, setContactName] = useState('');
  const [contactEmail, setContactEmail] = useState('');
  const [message, setMessage] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent'>('idle');
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    if (organisationName.trim().length < 2 || contactName.trim().length < 2) {
      setError('Enter your organisation name and your name (at least 2 characters each).');
      return;
    }
    if (!isValidEmail(contactEmail)) {
      setError('Enter a valid work email address.');
      return;
    }
    setStatus('sending');
    try {
      await apiOrgSubmitRequest({
        organisation_name: organisationName.trim(),
        contact_name: contactName.trim(),
        contact_email: contactEmail.trim(),
        ...(message.trim() ? { message: message.trim() } : {}),
      });
      setStatus('sent');
    } catch (err) {
      setStatus('idle');
      setError(err instanceof Error ? err.message : 'We could not send your request. Please try again.');
    }
  };

  if (status === 'sent') {
    return (
      <div className="org-request-done" role="status">
        <span className="org-request-done-icon" aria-hidden="true">
          <CheckCircle2 size={22} />
        </span>
        <h3>Request received</h3>
        <p>{REQUEST_SUCCESS_MESSAGE}</p>
      </div>
    );
  }

  return (
    <form className="auth-form org-request-form" onSubmit={handleSubmit} noValidate>
      {error && (
        <div className="auth-error" role="alert">
          <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
      <div className="auth-field">
        <label htmlFor="org-request-name">Organisation name</label>
        <div className="auth-input">
          <Building2 aria-hidden="true" />
          <input
            id="org-request-name"
            type="text"
            required
            maxLength={120}
            autoComplete="organization"
            value={organisationName}
            onChange={(e) => setOrganisationName(e.target.value)}
            placeholder="Your company"
          />
        </div>
      </div>
      <div className="org-form-row">
        <div className="auth-field">
          <label htmlFor="org-request-contact">Your name</label>
          <div className="auth-input">
            <User aria-hidden="true" />
            <input
              id="org-request-contact"
              type="text"
              required
              maxLength={120}
              autoComplete="name"
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
              placeholder="Full name"
            />
          </div>
        </div>
        <div className="auth-field">
          <label htmlFor="org-request-email">Work email</label>
          <div className="auth-input">
            <Mail aria-hidden="true" />
            <input
              id="org-request-email"
              type="email"
              required
              maxLength={255}
              autoComplete="email"
              inputMode="email"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
              placeholder="name@company.com"
            />
          </div>
        </div>
      </div>
      <div className="auth-field">
        <label htmlFor="org-request-message">
          What will your team use Clyptus.AI for? <span>(optional)</span>
        </label>
        <textarea
          id="org-request-message"
          className="org-textarea"
          rows={3}
          maxLength={MESSAGE_MAX}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="For example: SAP BRIM implementation team of 12 consultants"
        />
      </div>
      <button type="submit" className="button button-brand auth-submit" disabled={status === 'sending'}>
        <span>{status === 'sending' ? 'Sending request…' : 'Request an organisation account'}</span>
        <ArrowRight size={15} aria-hidden="true" />
      </button>
      <p className="org-form-note">
        A Clyptus Super Admin reviews every request. Approved organisations receive a single-use activation code.
      </p>
    </form>
  );
}
