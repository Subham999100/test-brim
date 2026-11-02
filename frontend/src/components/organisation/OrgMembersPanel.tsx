import React, { useCallback, useEffect, useState } from 'react';
import { KeyRound, RefreshCw, UserPlus } from 'lucide-react';
import type { OrgMember, OrgRole, User } from '../../types';
import {
  apiOrgAdminCreateMember,
  apiOrgAdminListMembers,
  apiOrgAdminResetPassword,
  apiOrgAdminUpdateMember,
} from '../../services/api';
import { ConfirmDialog, OrgModal } from './OrgDialog';
import { OneTimeSecret } from './OneTimeSecret';
import { ORG_ROLE_LABELS, formatDateTime, isValidEmail } from './orgFormat';

type AssignableRole = Exclude<OrgRole, 'owner'>;

type Pending =
  | { kind: 'deactivate'; member: OrgMember }
  | { kind: 'reset'; member: OrgMember };

const errorText = (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback);

/** Members table with add, role change, activate/deactivate and password reset (owner/admin only). */
export function OrgMembersPanel({ currentUser }: { currentUser: User | null }) {
  const [members, setMembers] = useState<OrgMember[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [pending, setPending] = useState<Pending | null>(null);
  const [pendingBusy, setPendingBusy] = useState(false);
  const [pendingError, setPendingError] = useState<string | null>(null);
  const [secret, setSecret] = useState<{ title: string; name: string; email: string; password: string } | null>(null);

  const isOwner = currentUser?.org_role === 'owner';

  const load = useCallback(async () => {
    try {
      setMembers(await apiOrgAdminListMembers());
      setLoadError(null);
    } catch (err) {
      setLoadError(errorText(err, 'Could not load members.'));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    apiOrgAdminListMembers()
      .then((data) => {
        if (!cancelled) setMembers(data);
      })
      .catch((err) => {
        if (!cancelled) setLoadError(errorText(err, 'Could not load members.'));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const replaceMember = (id: string, patch: Partial<OrgMember>) =>
    setMembers((prev) => prev?.map((m) => (m.id === id ? { ...m, ...patch } : m)) ?? prev);

  const changeRole = async (member: OrgMember, role: AssignableRole) => {
    if (role === member.org_role) return;
    setBusyId(member.id);
    setRowError(null);
    setNotice(null);
    try {
      const updated = await apiOrgAdminUpdateMember(member.id, { org_role: role });
      replaceMember(member.id, updated ?? { org_role: role });
      setNotice(`${member.name} is now ${ORG_ROLE_LABELS[role].toLowerCase()}.`);
    } catch (err) {
      setRowError(errorText(err, 'Could not change the role.'));
    } finally {
      setBusyId(null);
    }
  };

  const activate = async (member: OrgMember) => {
    setBusyId(member.id);
    setRowError(null);
    setNotice(null);
    try {
      const updated = await apiOrgAdminUpdateMember(member.id, { is_active: true });
      replaceMember(member.id, updated ?? { is_active: true });
      setNotice(`${member.name} can sign in again.`);
    } catch (err) {
      setRowError(errorText(err, 'Could not activate the member.'));
    } finally {
      setBusyId(null);
    }
  };

  const confirmPending = async () => {
    if (!pending) return;
    setPendingBusy(true);
    setPendingError(null);
    const { member } = pending;
    try {
      if (pending.kind === 'deactivate') {
        const updated = await apiOrgAdminUpdateMember(member.id, { is_active: false });
        replaceMember(member.id, updated ?? { is_active: false });
        setNotice(`${member.name} has been deactivated and signed out.`);
      } else {
        const { temporary_password } = await apiOrgAdminResetPassword(member.id);
        replaceMember(member.id, { must_change_password: true });
        setSecret({ title: 'Password reset', name: member.name, email: member.email, password: temporary_password });
      }
      setPending(null);
    } catch (err) {
      setPendingError(errorText(err, 'That did not work. Please try again.'));
    } finally {
      setPendingBusy(false);
    }
  };

  return (
    <section className="org-panel" aria-labelledby="org-members-title">
      <div className="org-panel-head">
        <div>
          <h2 id="org-members-title">Members</h2>
          <p>Each member gets individual credentials. New members set their own password at first sign-in.</p>
        </div>
        <div className="org-app-actions">
          <button type="button" className="org-btn" onClick={() => void load()}>
            <RefreshCw size={14} aria-hidden="true" /> Refresh
          </button>
          <button type="button" className="org-btn org-btn-primary" onClick={() => setAdding(true)}>
            <UserPlus size={15} aria-hidden="true" /> Add member
          </button>
        </div>
      </div>

      {notice && (
        <p className="org-notice" role="status">
          {notice}
        </p>
      )}
      {(rowError || loadError) && (
        <p className="org-alert" role="alert">
          {rowError ?? loadError}
        </p>
      )}

      {!members && !loadError && (
        <p className="org-form-note" role="status">
          Loading members…
        </p>
      )}

      {members && (
        <div className="org-table-wrap">
          <table className="org-table">
            <thead>
              <tr>
                <th scope="col">Member</th>
                <th scope="col">Role</th>
                <th scope="col">Status</th>
                <th scope="col">Last sign-in</th>
                <th scope="col">
                  <span className="visually-hidden">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => {
                const isSelf = member.id === currentUser?.id;
                const locked = isSelf || member.org_role === 'owner';
                const busy = busyId === member.id;
                return (
                  <tr key={member.id}>
                    <td>
                      <strong>
                        {member.name}
                        {isSelf ? ' (you)' : ''}
                      </strong>
                      <small>{member.email}</small>
                    </td>
                    <td>
                      {isOwner && !locked ? (
                        <>
                          <label htmlFor={`org-role-${member.id}`} className="visually-hidden">
                            Role for {member.name}
                          </label>
                          <select
                            id={`org-role-${member.id}`}
                            className="org-select org-select-sm"
                            value={member.org_role}
                            disabled={busy}
                            onChange={(e) => changeRole(member, e.target.value as AssignableRole)}
                          >
                            <option value="member">Member</option>
                            <option value="admin">Admin</option>
                          </select>
                        </>
                      ) : (
                        <span className={`org-badge${member.org_role !== 'member' ? ' org-badge-brand' : ''}`}>
                          {ORG_ROLE_LABELS[member.org_role] ?? member.org_role}
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={`org-badge ${member.is_active ? 'org-badge-active' : 'org-badge-danger'}`}>
                        {member.is_active ? 'Active' : 'Deactivated'}
                      </span>
                      {member.must_change_password && member.is_active && <small>Password change pending</small>}
                    </td>
                    <td>{member.last_login_at ? formatDateTime(member.last_login_at) : 'Never'}</td>
                    <td>
                      <div className="org-row-actions">
                        {!locked && (
                          <button
                            type="button"
                            className="org-btn org-btn-sm"
                            disabled={busy}
                            onClick={() => {
                              setPendingError(null);
                              setPending({ kind: 'reset', member });
                            }}
                          >
                            <KeyRound size={13} aria-hidden="true" /> Reset password
                          </button>
                        )}
                        {!locked &&
                          (member.is_active ? (
                            <button
                              type="button"
                              className="org-btn org-btn-sm org-btn-danger"
                              disabled={busy}
                              onClick={() => {
                                setPendingError(null);
                                setPending({ kind: 'deactivate', member });
                              }}
                            >
                              Deactivate
                            </button>
                          ) : (
                            <button type="button" className="org-btn org-btn-sm" disabled={busy} onClick={() => activate(member)}>
                              Activate
                            </button>
                          ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {adding && (
        <AddMemberModal
          canGrantAdmin={isOwner}
          onClose={() => setAdding(false)}
          onCreated={(member, password) => {
            setMembers((prev) => (prev ? [...prev, member] : [member]));
            setAdding(false);
            setSecret({ title: 'Member added', name: member.name, email: member.email, password });
          }}
        />
      )}

      {pending && (
        <ConfirmDialog
          title={pending.kind === 'deactivate' ? `Deactivate ${pending.member.name}?` : `Reset password for ${pending.member.name}?`}
          message={
            pending.kind === 'deactivate' ? (
              <p>They will be signed out at once and cannot sign in until you activate them again. Their shared answers stay in the hub.</p>
            ) : (
              <p>
                A new temporary password is generated and their current sessions end. They must set a new password at their next sign-in.
              </p>
            )
          }
          confirmLabel={pending.kind === 'deactivate' ? 'Deactivate member' : 'Reset password'}
          tone={pending.kind === 'deactivate' ? 'danger' : 'default'}
          busy={pendingBusy}
          error={pendingError}
          onConfirm={confirmPending}
          onCancel={() => setPending(null)}
        />
      )}

      {secret && (
        <OrgModal
          title={secret.title}
          description={
            <>
              Give this temporary password to <strong>{secret.name}</strong> ({secret.email}). They sign in at{' '}
              <strong>/organisation/login</strong> and must choose a new password straight away.
            </>
          }
          onClose={() => setSecret(null)}
        >
          <OneTimeSecret label="Temporary password" value={secret.password} />
          <div className="org-modal-actions">
            <button type="button" className="org-btn org-btn-primary" onClick={() => setSecret(null)}>
              I have copied it
            </button>
          </div>
        </OrgModal>
      )}
    </section>
  );
}

function AddMemberModal({
  canGrantAdmin,
  onClose,
  onCreated,
}: {
  canGrantAdmin: boolean;
  onClose: () => void;
  onCreated: (member: OrgMember, temporaryPassword: string) => void;
}) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<AssignableRole>('member');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return setError('Enter the member’s name.');
    if (!isValidEmail(email)) return setError('Enter a valid email address.');
    setBusy(true);
    setError(null);
    try {
      const created = await apiOrgAdminCreateMember({ name: name.trim(), email: email.trim(), org_role: role });
      onCreated(created.member, created.temporary_password);
    } catch (err) {
      setError(errorText(err, 'Could not add the member.'));
      setBusy(false);
    }
  };

  return (
    <OrgModal
      title="Add a member"
      description="A temporary password is generated for the new member and shown once."
      onClose={busy ? () => undefined : onClose}
    >
      <form className="org-form" onSubmit={submit} noValidate>
        {error && (
          <p className="org-alert" role="alert">
            {error}
          </p>
        )}
        <div className="org-field">
          <label htmlFor="org-member-name">Full name</label>
          <input
            id="org-member-name"
            className="org-input"
            type="text"
            autoComplete="off"
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div className="org-field">
          <label htmlFor="org-member-email">Work email</label>
          <input
            id="org-member-email"
            className="org-input"
            type="email"
            autoComplete="off"
            inputMode="email"
            maxLength={255}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="org-field">
          <label htmlFor="org-member-role">Role</label>
          <select
            id="org-member-role"
            className="org-select"
            value={role}
            onChange={(e) => setRole(e.target.value as AssignableRole)}
          >
            <option value="member">Member: chat and the knowledge hub</option>
            {canGrantAdmin && <option value="admin">Admin: also manages members and settings</option>}
          </select>
          {!canGrantAdmin && <small>Only the organisation owner can add admins.</small>}
        </div>
        <div className="org-modal-actions">
          <button type="button" className="org-btn org-btn-ghost" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="org-btn org-btn-primary" disabled={busy}>
            {busy ? 'Adding…' : 'Add member'}
          </button>
        </div>
      </form>
    </OrgModal>
  );
}
