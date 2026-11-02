import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import {
  formatActivationCode,
  validateActivationCode,
  validateNewPassword,
} from '../../components/organisation/orgFormat';

vi.mock('../../context/AuthContext', () => ({ useAuth: () => ({ user: null, applySession: vi.fn() }) }));

const { OrgActivatePage } = await import('./OrgActivatePage');
const { ActivationAccountForm } = await import('../../components/organisation/ActivationAccountForm');

const tagFor = (html: string, id: string) => html.match(new RegExp(`<input[^>]*id="${id}"[^>]*>`))?.[0] ?? '';

describe('OrgActivatePage step 1', () => {
  const html = renderToStaticMarkup(
    <MemoryRouter initialEntries={['/organisation/activate']}>
      <OrgActivatePage />
    </MemoryRouter>,
  );

  it('asks for the activation code in the sign-in layout', () => {
    expect(html.indexOf('class="auth-visual"')).toBeLessThan(html.indexOf('class="auth-form-side"'));
    expect(html).toContain('Activate your organisation');
    expect(html).toContain('for="org-activation-code"');
    const input = tagFor(html, 'org-activation-code');
    expect(input).toContain('autoComplete="one-time-code"');
    expect(input).toContain('placeholder="CLY-XXXX-XXXX-XXXX-XXXX"');
    expect(html).toMatch(/aria-current="step"[^>]*>.*?Verify code/);
    expect(html).not.toContain('id="org-activate-password"');
  });
});

describe('ActivationAccountForm (step 2)', () => {
  const html = renderToStaticMarkup(
    <ActivationAccountForm
      details={{
        organisation_name: 'Acme Telco',
        admin_email: 'owner@acme.example',
        admin_name: 'Olivia Owner',
        expires_at: '2026-11-04T12:00:00Z',
      }}
      submitting={false}
      error={null}
      onSubmit={() => {}}
      onBack={() => {}}
    />,
  );

  it('shows the organisation and admin email and asks for name and a confirmed password', () => {
    expect(html).toContain('Acme Telco');
    expect(html).toContain('owner@acme.example');
    expect(tagFor(html, 'org-activate-name')).toContain('value="Olivia Owner"');
    for (const id of ['org-activate-password', 'org-activate-confirm']) {
      const input = tagFor(html, id);
      expect(input).toContain('minLength="12"');
      expect(input).toContain('maxLength="72"');
      expect(input).toContain('autoComplete="new-password"');
      expect(html).toContain(`for="${id}"`);
    }
    expect(html).toContain('12–72 characters.');
  });

  it('shows a server error as an alert', () => {
    const withError = renderToStaticMarkup(
      <ActivationAccountForm
        details={{ organisation_name: 'A', admin_email: 'a@b.co', admin_name: 'A', expires_at: '2026-11-04T12:00:00Z' }}
        submitting={false}
        error="This activation code is not valid. Ask your Clyptus administrator for a new code."
        onSubmit={() => {}}
        onBack={() => {}}
      />,
    );
    expect(withError).toMatch(/role="alert"[^>]*>.*?This activation code is not valid/);
  });
});

describe('activation validation', () => {
  it('formats codes typed with spaces, lower case or without the prefix', () => {
    expect(formatActivationCode('cly abcd efgh jkmn pqrs')).toBe('CLY-ABCD-EFGH-JKMN-PQRS');
    expect(formatActivationCode('ABCDEFGHJKMNPQRS')).toBe('CLY-ABCD-EFGH-JKMN-PQRS');
    expect(formatActivationCode('')).toBe('');
  });

  it('rejects empty and incomplete codes before calling the server', () => {
    expect(validateActivationCode('')).toMatch(/Enter the activation code/);
    expect(validateActivationCode('CLY-ABCD-EFGH')).toMatch(/full activation code/);
    expect(validateActivationCode('CLY-ABCD-EFGH-JKMN-PQRS')).toBeNull();
  });

  it('enforces 12-72 characters and a matching confirmation', () => {
    expect(validateNewPassword('short', 'short')).toMatch(/at least 12/);
    expect(validateNewPassword('x'.repeat(73), 'x'.repeat(73))).toMatch(/at most 72/);
    expect(validateNewPassword('long-enough-pass', 'long-enough-pasS')).toMatch(/do not match/);
    expect(validateNewPassword('long-enough-pass', 'long-enough-pass')).toBeNull();
  });
});
