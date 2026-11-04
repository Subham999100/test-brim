import type { OrganisationStatus, OrgRole } from '../../types';

// Mirrors the backend password rules (12-72 characters).
export const PASSWORD_MIN = 12;
export const PASSWORD_MAX = 72;
export const COMMENT_MAX = 2000;

/** Knowledge hub categories (key → label), in the contract's order. */
export const KNOWLEDGE_CATEGORIES: ReadonlyArray<{ key: string; label: string }> = [
  { key: 'cc', label: 'Convergent Charging (CC)' },
  { key: 'ci', label: 'Convergent Invoicing (CI)' },
  { key: 'som', label: 'Subscription Order Management (SOM)' },
  { key: 'fica', label: 'FI-CA' },
  { key: 'integration', label: 'SAP BRIM Integration' },
  { key: 'troubleshooting', label: 'Troubleshooting' },
  { key: 'architecture', label: 'Architecture and Configuration' },
  { key: 'general', label: 'General SAP' },
];

export const ORG_STATUS_LABELS: Record<OrganisationStatus, string> = {
  requested: 'Requested',
  pending_activation: 'Pending activation',
  active: 'Active',
  suspended: 'Suspended',
  deactivated: 'Deactivated',
  rejected: 'Rejected',
};

export const ORG_ROLE_LABELS: Record<OrgRole, string> = {
  owner: 'Owner',
  admin: 'Admin',
  member: 'Member',
};

/** Plain text for one-line previews of Markdown answers: drops emphasis, code, heading, quote and list
 *  markers and keeps link text. Full answers are still rendered as Markdown in the detail view. */
export const markdownToPlainText = (markdown: string): string =>
  (markdown || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/(\*\*|__)(.*?)\1/g, '$2')
    .replace(/(^|[\s(])[*_]([^*_\n]+)[*_](?=[\s).,;:!?]|$)/g, '$1$2')
    .replace(/^\s{0,3}(?:#{1,6}\s+|>\s?|[-*+]\s+|\d+[.)]\s+)/gm, '')
    .replace(/\s+/g, ' ')
    .trim();

const asDate = (iso: string | null | undefined): Date | null => {
  if (!iso) return null;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
};

/** "1 Nov 2026"; an em dash for missing or invalid dates. */
export const formatDate = (iso: string | null | undefined): string => {
  const date = asDate(iso);
  return date ? date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : '—';
};

/** "1 Nov 2026, 14:05" in the viewer's time zone. */
export const formatDateTime = (iso: string | null | undefined): string => {
  const date = asDate(iso);
  return date
    ? date.toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
    : '—';
};

export const pluralise = (count: number, singular: string, plural = `${singular}s`): string =>
  `${count} ${count === 1 ? singular : plural}`;

export const initials = (name: string | null | undefined): string => {
  const parts = (name ?? '').trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
};

/** "Liked by Priya" / "Priya and Daniel" / "Priya, Daniel and 3 others". */
export const likersSummary = (names: string[]): string => {
  if (names.length === 0) return 'No likes yet';
  if (names.length === 1) return `Liked by ${names[0]}`;
  if (names.length === 2) return `Liked by ${names[0]} and ${names[1]}`;
  const others = names.length - 2;
  return `Liked by ${names[0]}, ${names[1]} and ${pluralise(others, 'other')}`;
};

/**
 * Formats what the user typed as `CLY-XXXX-XXXX-XXXX-XXXX`. The backend normalises again before hashing;
 * this only makes the code readable and catches incomplete codes before a request.
 */
export const formatActivationCode = (input: string): string => {
  let body = input.toUpperCase().replace(/[^A-Z0-9]/g, '');
  if (body.startsWith('CLY')) body = body.slice(3);
  const groups = body.slice(0, 16).match(/.{1,4}/g) ?? [];
  return groups.length ? `CLY-${groups.join('-')}` : '';
};

export const validateActivationCode = (input: string): string | null => {
  const formatted = formatActivationCode(input);
  if (!formatted) return 'Enter the activation code from your Clyptus administrator.';
  if (formatted.replace(/-/g, '').length !== 19) {
    return 'Enter the full activation code, in the format CLY-XXXX-XXXX-XXXX-XXXX.';
  }
  return null;
};

export const validateNewPassword = (password: string, confirm: string): string | null => {
  if (password.length < PASSWORD_MIN) return `Use at least ${PASSWORD_MIN} characters for your password.`;
  if (password.length > PASSWORD_MAX) return `Use at most ${PASSWORD_MAX} characters for your password.`;
  if (password !== confirm) return 'The two passwords do not match.';
  return null;
};

/** A starting or reset password an organisation admin types for a member (same 12-72 rule). */
export const validateMemberPassword = (password: string): string | null => {
  if (password.length < PASSWORD_MIN) return `Enter a password of at least ${PASSWORD_MIN} characters.`;
  if (password.length > PASSWORD_MAX) return `Use at most ${PASSWORD_MAX} characters for the password.`;
  return null;
};

export const isValidEmail = (email: string): boolean => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());

/** Copies text; resolves false when the clipboard is unavailable (insecure context, denied permission). */
export const copyText = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
};
