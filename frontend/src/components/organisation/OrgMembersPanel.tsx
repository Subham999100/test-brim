import React, { useCallback, useEffect, useState } from 'react';
import { Eye, EyeOff, KeyRound, RefreshCw, UserPlus } from 'lucide-react';
import type { OrgMember, OrgRole, User } from '../../types';
import {
  apiOrgAdminCreateMember,
  apiOrgAdminListMembers,
  apiOrgAdminResetPassword,
  apiOrgAdminUpdateMember,
} from '../../services/api';
import { ConfirmDialog, OrgModal } from './OrgDialog';
import { ORG_ROLE_LABELS, PASSWORD_MAX, PASSWORD_MIN, formatDateTime, isValidEmail, validateMemberPassword } from './orgFormat';

type AssignableRole = Exclude<OrgRole, 'owner'>;

const errorText = (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback);

/** Members table with add, role change, activate/deactivate and password reset (owner/admin only). The admin
 *  sets each member's e-mail and starting password; the member chooses their own at the first sign-in. */
export function OrgMembersPanel({ currentUser }: { currentUser: User | null }) {
  const [members, setMembers] = useState<OrgMember[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [rowError, setRowError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [deactivating, setDeactivating] = useState<OrgMember | null>(null);
  const [pendingBusy, setPendingBusy] = useState(false);
  const [pendingError, setPendingError] = useState<string | null>(null);
  const [resetting, setResetting] = useState<OrgMember | null>(null);

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

  const confirmDeactivate = async () => {
    if (!deactivating) return;
    setPendingBusy(true);
    setPendingError(null);
    const member = deactivating;
    try {
      const updated = await apiOrgAdminUpdateMember(member.id, { is_active: false });
      replaceMember(member.id, updated ?? { is_active: false });
      setNotice(`${member.name} has been deactivated and signed out.`);
      setDeactivating(null);
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
                              setNotice(null);
                              setResetting(member);
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
                                setDeactivating(member);
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
          onCreated={(member) => {
            setMembers((prev) => (prev ? [...prev, member] : [member]));
            setAdding(false);
            setNotice(
              `${member.name} was added. They sign in at /organisation/login with ${member.email} and the password you set, then choose their own.`,
            );
          }}
        />
      )}

      {resetting && (
        <ResetPasswordModal
          member={resetting}
          onClose={() => setResetting(null)}
          onReset={(updated) => {
            replaceMember(updated.id, updated);
            setResetting(null);
            setNotice(`New password set for ${updated.name}. They were signed out and choose their own password at their next sign-in.`);
          }}
        />
      )}

      {deactivating && (
        <ConfirmDialog
          title={`Deactivate ${deactivating.name}?`}
          message={
            <p>They will be signed out at once and cannot sign in until you activate them again. Their shared answers stay in the hub.</p>
          }
          confirmLabel="Deactivate member"
          tone="danger"
          busy={pendingBusy}
          error={pendingError}
          onConfirm={confirmDeactivate}
          onCancel={() => setDeactivating(null)}
        />
      )}
    </section>
  );
}

/** Password input with a show/hide toggle for passwords the admin sets for a member. */
function MemberPasswordField({
  id,
  label,
  hint,
  value,
  onChange,
}: {
  id: string;
  label: string;
  hint: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="org-field">
      <label htmlFor={id}>{label}</label>
      <div className="org-password">
        <input
          id={id}
          className="org-input"
          type={visible ? 'text' : 'password'}
          autoComplete="new-password"
          spellCheck={false}
          minLength={PASSWORD_MIN}
          maxLength={PASSWORD_MAX}
          aria-describedby={`${id}-hint`}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
        <button
          type="button"
          className="org-password-toggle"
          aria-label={visible ? 'Hide password' : 'Show password'}
          aria-pressed={visible}
          onClick={() => setVisible((v) => !v)}
        >
          {visible ? <EyeOff size={16} aria-hidden="true" /> : <Eye size={16} aria-hidden="true" />}
        </button>
      </div>
      <small id={`${id}-hint`}>{hint}</small>
    </div>
  );
}

/** The admin types a new password for a member; their sessions end and they choose their own at the next sign-in. */
export function ResetPasswordModal({
  member,
  onClose,
  onReset,
}: {
  member: OrgMember;
  onClose: () => void;
  onReset: (updated: OrgMember) => void;
}) {
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const problem = validateMemberPassword(password);
    if (problem) return setError(problem);
    setBusy(true);
    setError(null);
    try {
      onReset(await apiOrgAdminResetPassword(member.id, password));
    } catch (err) {
      setError(errorText(err, 'Could not reset the password.'));
      setBusy(false);
    }
  };

  return (
    <OrgModal
      title={`Reset password for ${member.name}`}
      description={
        <>
          Type a new password for {member.email}. Their current sessions are signed out, and they choose their own
          password at their next sign-in. Nothing is e-mailed: share it with them yourself.
        </>
      }
      onClose={busy ? () => undefined : onClose}
    >
      <form className="org-form" onSubmit={submit} noValidate>
        {error && (
          <p className="org-alert" role="alert">
            {error}
          </p>
        )}
        <MemberPasswordField
          id="org-reset-password"
          label="New password"
          hint={`${PASSWORD_MIN}–${PASSWORD_MAX} characters.`}
          value={password}
          onChange={setPassword}
        />
        <div className="org-modal-actions">
          <button type="button" className="org-btn org-btn-ghost" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="org-btn org-btn-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Set new password'}
          </button>
        </div>
      </form>
    </OrgModal>
  );
}

export function AddMemberModal({
  canGrantAdmin,
  onClose,
  onCreated,
}: {
  canGrantAdmin: boolean;
  onClose: () => void;
  onCreated: (member: OrgMember) => void;
}) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<AssignableRole>('member');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return setError('Enter the member’s name.');
    if (!isValidEmail(email)) return setError('Enter a valid email address.');
    const problem = validateMemberPassword(password);
    if (problem) return setError(problem);
    setBusy(true);
    setError(null);
    try {
      const created = await apiOrgAdminCreateMember({ name: name.trim(), email: email.trim(), password, org_role: role });
      onCreated(created.member);
    } catch (err) {
      setError(errorText(err, 'Could not add the member.'));
      setBusy(false);
    }
  };

  return (
    <OrgModal
      title="Add a member"
      description="Set their sign-in e-mail and a starting password. Nothing is e-mailed: share both with them yourself."
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
        <MemberPasswordField
          id="org-member-password"
          label="Password"
          hint={`${PASSWORD_MIN}–${PASSWORD_MAX} characters. They choose their own password at their first sign-in.`}
          value={password}
          onChange={setPassword}
        />
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
