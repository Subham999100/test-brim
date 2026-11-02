import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import type { AdminOrganisationDetail } from '../../types';
import { apiAdminGetOrganisation } from '../../services/api';
import { ORG_ROLE_LABELS, ORG_STATUS_LABELS, formatDate, formatDateTime } from '../organisation/orgFormat';

const USAGE_LABELS: Array<[keyof AdminOrganisationDetail['usage'], string]> = [
  ['members', 'Members'],
  ['active_members', 'Active members'],
  ['questions_30d', 'Questions (30 days)'],
  ['shared_answers', 'Shared answers'],
  ['comments', 'Comments'],
];

/** Super Admin detail for one organisation: profile, administrators and usage. */
export function OrganisationDetailPanel({ organisationId, onClose }: { organisationId: string; onClose: () => void }) {
  const [detail, setDetail] = useState<AdminOrganisationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiAdminGetOrganisation(organisationId)
      .then((data) => {
        if (!cancelled) setDetail(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load the organisation.');
      });
    return () => {
      cancelled = true;
    };
  }, [organisationId]);

  const org = detail?.organisation;

  return (
    <section id="admin-org-detail" className="org-detail" aria-label="Organisation details">
      <div className="org-panel-head" style={{ marginBottom: 12 }}>
        <div>
          <h2>{org?.name ?? 'Organisation details'}</h2>
          {org && (
            <p>
              {ORG_STATUS_LABELS[org.status] ?? org.status} · created {formatDate(org.created_at)}
              {org.activated_at ? ` · activated ${formatDate(org.activated_at)}` : ''}
            </p>
          )}
        </div>
        <button type="button" className="org-icon-btn" onClick={onClose} aria-label="Close organisation details">
          <X size={17} aria-hidden="true" />
        </button>
      </div>

      {error && (
        <p className="org-alert" role="alert">
          {error}
        </p>
      )}
      {!detail && !error && (
        <p className="org-form-note" role="status">
          Loading details…
        </p>
      )}

      {detail && org && (
        <>
          <div className="org-stat-grid">
            {USAGE_LABELS.map(([key, label]) => (
              <div className="org-stat" key={key}>
                <strong>{detail.usage?.[key] ?? 0}</strong>
                <span>{label}</span>
              </div>
            ))}
          </div>
          <div className="org-detail-grid">
            <div>
              <h3 className="org-section-title">Contact</h3>
              <dl className="org-dl">
                <div>
                  <dt>Name</dt>
                  <dd>{org.contact_name || '—'}</dd>
                </div>
                <div>
                  <dt>Email</dt>
                  <dd>{org.contact_email}</dd>
                </div>
                {org.active_code && (
                  <div>
                    <dt>Active code</dt>
                    <dd>
                      ••••{org.active_code.hint}, expires {formatDateTime(org.active_code.expires_at)}
                    </dd>
                  </div>
                )}
              </dl>
              {org.request_message && (
                <>
                  <h3 className="org-section-title" style={{ marginTop: 14 }}>
                    Request message
                  </h3>
                  <p className="org-form-note" style={{ whiteSpace: 'pre-wrap' }}>
                    {org.request_message}
                  </p>
                </>
              )}
            </div>
            <div>
              <h3 className="org-section-title">Administrators</h3>
              {detail.admins.length === 0 ? (
                <p className="org-form-note">No administrator account yet (not activated).</p>
              ) : (
                <dl className="org-dl">
                  {detail.admins.map((admin) => (
                    <div key={admin.email}>
                      <dt>
                        {admin.name}
                        <br />
                        <small>{admin.email}</small>
                      </dt>
                      <dd>
                        {ORG_ROLE_LABELS[admin.org_role] ?? admin.org_role}
                        {admin.is_active ? '' : ' (inactive)'}
                        <br />
                        <small>{admin.last_login_at ? `Last sign-in ${formatDateTime(admin.last_login_at)}` : 'Never signed in'}</small>
                      </dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
