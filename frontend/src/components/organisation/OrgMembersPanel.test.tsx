import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it, vi } from 'vitest';
import type { OrgMember } from '../../types';
import { AddMemberModal, ResetPasswordModal } from './OrgMembersPanel';
import { validateMemberPassword } from './orgFormat';

const member: OrgMember = {
  id: 'm1',
  name: 'Asha Rao',
  email: 'asha@example.com',
  org_role: 'member',
  is_active: true,
  must_change_password: false,
  created_at: '2026-11-01T10:00:00Z',
  last_login_at: null,
};

describe('Add member: the admin sets the e-mail and password', () => {
  const html = renderToStaticMarkup(<AddMemberModal canGrantAdmin onClose={vi.fn()} onCreated={vi.fn()} />);

  it('asks for name, e-mail, a password and the role', () => {
    expect(html).toContain('id="org-member-name"');
    expect(html).toContain('id="org-member-email"');
    expect(html).toMatch(/<input[^>]*id="org-member-password"[^>]*>/);
    const password = html.match(/<input[^>]*id="org-member-password"[^>]*>/)![0];
    expect(password).toContain('type="password"');
    expect(password).toContain('minLength="12"');
    expect(password).toContain('maxLength="72"');
    expect(password).toContain('autoComplete="new-password"');
    expect(html).toContain('id="org-member-role"');
  });

  it('lets the admin reveal what they typed', () => {
    expect(html).toMatch(/<button[^>]*aria-label="Show password"[^>]*aria-pressed="false"/);
  });

  it('no longer promises a generated temporary password', () => {
    expect(html).not.toMatch(/generated/i);
    expect(html).toMatch(/choose their own password at their first sign-in/);
  });
});

describe('Reset password: the admin types the new password', () => {
  const html = renderToStaticMarkup(
    <ResetPasswordModal member={member} onClose={vi.fn()} onReset={vi.fn()} />,
  );

  it('names the member and asks for a new password', () => {
    expect(html).toContain('Reset password for Asha Rao');
    expect(html).toMatch(/<input[^>]*id="org-reset-password"[^>]*type="password"/);
    expect(html).toMatch(/signed out/);
    expect(html).not.toMatch(/generated/i);
  });
});

describe('validateMemberPassword', () => {
  it('follows the organisation password rule of 12-72 characters', () => {
    expect(validateMemberPassword('')).toBe('Enter a password of at least 12 characters.');
    expect(validateMemberPassword('elevenchars')).toBe('Enter a password of at least 12 characters.');
    expect(validateMemberPassword('x'.repeat(73))).toBe('Use at most 72 characters for the password.');
    expect(validateMemberPassword('twelve-chars')).toBeNull();
  });
});
