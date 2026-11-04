import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: null, login: vi.fn(), register: vi.fn() }),
}));

const { LoginPage } = await import('./LoginPage');

const render = (path: string) =>
  renderToStaticMarkup(
    <MemoryRouter initialEntries={[path]}>
      <LoginPage />
    </MemoryRouter>,
  );

const tagFor = (html: string, id: string) => html.match(new RegExp(`<input[^>]*id="${id}"[^>]*>`))?.[0] ?? '';

describe('LoginPage', () => {
  it('puts the brand visual first (left) and the form second (right)', () => {
    const html = render('/login');
    const visual = html.indexOf('class="auth-visual"');
    const form = html.indexOf('class="auth-form-side"');

    expect(visual).toBeGreaterThan(-1);
    expect(form).toBeGreaterThan(visual);
    expect(html).toMatch(/<svg class="auth-visual-art"[^>]*role="img"[^>]*aria-label="SAP BRIM flow/);
  });

  it('shows a security shield followed by a quotation instead of the old session notice', () => {
    const html = render('/login');

    expect(html).not.toContain('Signed, short-lived sessions');
    expect(html).not.toContain('login-safe');
    expect(html.indexOf('auth-quote-icon')).toBeLessThan(html.indexOf('<blockquote>'));
    expect(html).toMatch(/<blockquote>“[^<]+”<\/blockquote>/);
  });

  it('has no "Back to home" link (the logo already leads home)', () => {
    for (const path of ['/login', '/login?mode=register']) {
      const html = render(path);
      expect(html).not.toContain('Back to home');
      expect(html).not.toContain('login-back');
      expect(html).toContain('aria-label="Clyptusap.ai home"');
    }
  });

  it('offers Create an organisation below the form as a link to the Organisation Portal', () => {
    const html = render('/login');

    expect(html.indexOf('Create an organisation')).toBeGreaterThan(html.indexOf('</form>'));
    expect(html).toMatch(/<a class="auth-org-button" aria-describedby="auth-org-note" href="\/organisation"/);
    expect(html).not.toContain('Coming soon');
    expect(html).not.toMatch(/auth-org-button[^>]*disabled/);
  });

  it('links every label to its input and sets sign-in autocomplete hints', () => {
    const html = render('/login?mode=login');

    for (const id of ['auth-email', 'auth-password']) expect(html).toContain(`for="${id}"`);
    // React's server renderer keeps camelCase attribute names; HTML treats them case-insensitively.
    expect(tagFor(html, 'auth-email')).toContain('autoComplete="username"');
    expect(tagFor(html, 'auth-password')).toContain('autoComplete="current-password"');
    expect(html).toContain('aria-label="Show password"');
    expect(html).toMatch(/role="tab" aria-selected="true"[^>]*>Sign In</);
  });

  it('applies the backend password rules when creating an account', () => {
    const html = render('/login?mode=register');
    const password = tagFor(html, 'auth-password');

    expect(password).toContain('minLength="8"');
    expect(password).toContain('maxLength="72"');
    expect(password).toContain('autoComplete="new-password"');
    expect(html).toContain('8–72 characters.');
    expect(html).toMatch(/role="tab" aria-selected="true"[^>]*>Create Account</);
  });

  it('after sign-up, shows the Sign In tab with an "Account created" note', () => {
    const html = render('/login?mode=login&created=1');

    expect(html).toMatch(/role="tab" aria-selected="true"[^>]*>Sign In</);
    expect(html).toMatch(/<p[^>]*role="status"[^>]*>[^<]*Account created\. Please sign in\./);
    expect(render('/login?mode=login')).not.toContain('Account created');
  });

  it('lets individuals create an account without any code (codes are for organisations only)', () => {
    const html = render('/login?mode=register');

    expect(html).not.toContain('auth-invite');
    expect(html).not.toMatch(/invite code/i);
  });
});
