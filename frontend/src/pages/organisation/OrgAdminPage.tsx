import React, { useEffect, useState } from 'react';
import { Activity, ArrowLeft, Settings2, Users } from 'lucide-react';
import { Link } from 'react-router-dom';
import { PageMeta } from '../../components/ui/PageMeta';
import { OrgMembersPanel } from '../../components/organisation/OrgMembersPanel';
import { OrgActivityPanel } from '../../components/organisation/OrgActivityPanel';
import { OrgSettingsPanel } from '../../components/organisation/OrgSettingsPanel';
import { ORG_ROLE_LABELS, ORG_STATUS_LABELS, initials, pluralise } from '../../components/organisation/orgFormat';
import { useAuth } from '../../context/AuthContext';
import { ORG_HUB_PATH } from '../../layouts/accountRouting';
import { apiOrgGetMe } from '../../services/api';
import type { OrgMe } from '../../types';
import '../../components/organisation/organisation.css';

type Tab = 'members' | 'activity' | 'settings';

const TABS: Array<{ id: Tab; label: string; icon: typeof Users }> = [
  { id: 'members', label: 'Members', icon: Users },
  { id: 'activity', label: 'Activity', icon: Activity },
  { id: 'settings', label: 'Settings', icon: Settings2 },
];

/** /app/organisation/admin: organisation owners and admins manage members, see activity and settings. */
export const OrgAdminPage: React.FC = () => {
  const { user } = useAuth();
  const [me, setMe] = useState<OrgMe | null>(null);
  const [nameOverride, setNameOverride] = useState<string | null>(null);
  const [contactOverride, setContactOverride] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('members');

  useEffect(() => {
    let cancelled = false;
    apiOrgGetMe()
      .then((data) => {
        if (!cancelled) setMe(data);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const organisationName = nameOverride ?? me?.organisation.name ?? user?.organization_name ?? 'Your organisation';
  const role = me?.role ?? user?.org_role ?? undefined;

  const onTabKey = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== 'ArrowRight' && event.key !== 'ArrowLeft') return;
    const index = TABS.findIndex((t) => t.id === tab);
    const next = TABS[(index + (event.key === 'ArrowRight' ? 1 : TABS.length - 1)) % TABS.length];
    setTab(next.id);
    document.getElementById(`org-admin-tab-${next.id}`)?.focus();
  };

  return (
    <>
      <PageMeta title="Organisation Admin" description="Manage your organisation's members, activity and settings." />
      <div className="org-app">
        <header className="org-app-header">
          <div className="org-app-identity">
            <span className="org-app-logo" aria-hidden="true">
              {initials(organisationName)}
            </span>
            <div>
              <span className="org-app-eyebrow">Organisation admin dashboard</span>
              <h1>{organisationName}</h1>
              <div className="org-app-meta">
                {role && <span className="org-badge org-badge-brand">{ORG_ROLE_LABELS[role] ?? role}</span>}
                {me && (
                  <span className={`org-badge ${me.organisation.status === 'active' ? 'org-badge-active' : 'org-badge-warn'}`}>
                    {ORG_STATUS_LABELS[me.organisation.status] ?? me.organisation.status}
                  </span>
                )}
                {me && <span>{pluralise(me.organisation.member_count, 'member')}</span>}
              </div>
            </div>
          </div>
          <div className="org-app-actions">
            <Link className="org-btn" to={ORG_HUB_PATH}>
              <ArrowLeft size={15} aria-hidden="true" /> Knowledge Hub
            </Link>
          </div>
        </header>

        <div className="org-tabs" role="tablist" aria-label="Organisation administration" onKeyDown={onTabKey}>
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`org-admin-tab-${id}`}
              type="button"
              role="tab"
              aria-selected={tab === id}
              aria-controls={`org-admin-panel-${id}`}
              tabIndex={tab === id ? 0 : -1}
              onClick={() => setTab(id)}
            >
              <Icon size={15} aria-hidden="true" />
              {label}
            </button>
          ))}
        </div>

        <div role="tabpanel" id={`org-admin-panel-${tab}`} aria-labelledby={`org-admin-tab-${tab}`}>
          {tab === 'members' && <OrgMembersPanel currentUser={user} />}
          {tab === 'activity' && <OrgActivityPanel />}
          {tab === 'settings' && (
            <OrgSettingsPanel
              key={me ? 'loaded' : 'loading'}
              organisationName={organisationName}
              contactEmail={contactOverride ?? me?.organisation.contact_email ?? ''}
              onSaved={({ name, contact_email }) => {
                if (name) setNameOverride(name);
                if (contact_email) setContactOverride(contact_email);
              }}
            />
          )}
        </div>
      </div>
    </>
  );
};
