import React, { useState } from 'react';
import { Save } from 'lucide-react';
import { apiOrgAdminUpdateOrganisation } from '../../services/api';
import { isValidEmail } from './orgFormat';

/** Organisation name and contact email (PATCH /org/admin/organisation). Only changed fields are sent. */
export function OrgSettingsPanel({
  organisationName,
  contactEmail: savedContactEmail = '',
  onSaved,
}: {
  organisationName: string;
  contactEmail?: string;
  onSaved: (changes: { name?: string; contact_email?: string }) => void;
}) {
  const [name, setName] = useState(organisationName);
  const [contactEmail, setContactEmail] = useState(savedContactEmail);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaved(false);
    const changes: { name?: string; contact_email?: string } = {};
    if (name.trim() && name.trim() !== organisationName) changes.name = name.trim();
    if (contactEmail.trim() && contactEmail.trim().toLowerCase() !== savedContactEmail.toLowerCase()) {
      if (!isValidEmail(contactEmail)) return setError('Enter a valid contact email address.');
      changes.contact_email = contactEmail.trim();
    }
    if (!name.trim()) return setError('The organisation name cannot be empty.');
    if (Object.keys(changes).length === 0) return setError('Nothing to save yet.');
    setBusy(true);
    setError(null);
    try {
      await apiOrgAdminUpdateOrganisation(changes);
      onSaved(changes);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the organisation settings.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="org-panel" aria-labelledby="org-settings-title">
      <div className="org-panel-head">
        <div>
          <h2 id="org-settings-title">Organisation settings</h2>
          <p>Shown to every member. Clyptus uses the contact email for account matters.</p>
        </div>
      </div>
      <form className="org-form org-settings-form" onSubmit={submit} noValidate>
        {error && (
          <p className="org-alert" role="alert">
            {error}
          </p>
        )}
        {saved && (
          <p className="org-notice" role="status">
            Settings saved.
          </p>
        )}
        <div className="org-field">
          <label htmlFor="org-settings-name">Organisation name</label>
          <input
            id="org-settings-name"
            className="org-input"
            type="text"
            autoComplete="organization"
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="org-field">
          <label htmlFor="org-settings-email">Contact email</label>
          <input
            id="org-settings-email"
            className="org-input"
            type="email"
            autoComplete="email"
            inputMode="email"
            maxLength={255}
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            placeholder="name@company.com"
          />
        </div>
        <div>
          <button type="submit" className="org-btn org-btn-primary" disabled={busy}>
            <Save size={14} aria-hidden="true" /> {busy ? 'Saving…' : 'Save settings'}
          </button>
        </div>
      </form>
    </section>
  );
}
