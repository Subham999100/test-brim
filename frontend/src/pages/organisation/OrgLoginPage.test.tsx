import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import type { User } from '../../types';

const auth = vi.hoisted(() => ({ user: null as User | null }));

vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: auth.user, orgLogin: vi.fn() }),
}));

const { OrgLoginPage } = await import('./OrgLoginPage');

const render = (user: User | null = null) => {
  auth.user = user;
  return renderToStaticMarkup(
    <MemoryRouter initialEntries={['/organisation/login']}>
      <OrgLoginPage />
    </MemoryRouter>,
  );
};

const individual: User = { id: 'u1', email: 'sam@example.com', name: 'Sam Lee', account_type: 'individual' };

describe('OrgLoginPage', () => {
  it('has its own organisation artwork, not the individual sign-in BRIM flow', () => {
    const html = render();

    expect(html).toMatch(/<svg class="auth-visual-art"[^>]*role="img"[^>]*aria-label="Organisation members/);
    expect(html).not.toContain('aria-label="SAP BRIM flow');
    expect(html.indexOf('class="auth-visual')).toBeLessThan(html.indexOf('class="auth-form-side"'));
  });

  it('explains the organisation workspace next to the artwork', () => {
    const html = render();

    expect(html).toContain('class="auth-points"');
    expect(html).toMatch(/Knowledge Hub organised by SAP BRIM topic/);
    expect(html).toMatch(/own sign-in/);
  });

  it('labels the form as the organisation sign-in', () => {
    const html = render();

    expect(html).toContain('ORGANISATION SIGN-IN');
    expect(html).toContain('<h1>Sign in to your organisation</h1>');
  });

  it('has no "Back to Organisation Portal" link (the logo already leads home)', () => {
    const html = render();

    expect(html).not.toContain('Back to Organisation Portal');
    expect(html).not.toContain('login-back');
  });

  it('gives first-time members the temporary-password hint under the password field, before the button', () => {
    const html = render();
    const password = html.match(/<input[^>]*id="org-login-password"[^>]*>/)?.[0] ?? '';

    expect(password).toContain('aria-describedby="org-login-password-hint"');
    expect(html).toMatch(/id="org-login-password-hint"[^>]*>[\s\S]*First sign-in\?/);
    expect(html.indexOf('First sign-in?')).toBeLessThan(html.indexOf('Sign in to workspace'));
    expect(html.lastIndexOf('</form>')).toBeGreaterThan(html.indexOf('Sign in to workspace'));
  });

  it('offers activation and personal sign-in as separate ways in', () => {
    const html = render();

    expect(html).toMatch(/<a class="org-auth-exit" href="\/organisation\/activate"/);
    expect(html).toMatch(/<a class="org-auth-exit" href="\/login"/);
  });

  // Regression: a signed-in individual was sent to /app before they could sign in to their organisation.
  it('keeps a signed-in individual on the form and explains how to switch', () => {
    const html = render(individual);

    expect(html).toContain('id="org-login-email"');
    expect(html).toMatch(/role="status"[\s\S]*signed in as[\s\S]*Sam Lee[\s\S]*individual account/);
    expect(render()).not.toMatch(/signed in as/);
  });
});
