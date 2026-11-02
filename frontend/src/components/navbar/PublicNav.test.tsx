import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';
import { PublicNav } from './PublicNav';

const html = renderToStaticMarkup(
  <MemoryRouter>
    <PublicNav />
  </MemoryRouter>,
);

const linksTo = (label: string) =>
  [...html.matchAll(/<a[^>]*href="([^"]*)"[^>]*>([^<]*)</g)]
    .filter(([, , text]) => text.trim() === label)
    .map(([, href]) => href.replace(/&amp;/g, '&'));

describe('PublicNav', () => {
  it('sends Sign up to the create-account tab, desktop and mobile', () => {
    expect(linksTo('Sign up')).toEqual(['/login?mode=register', '/login?mode=register']);
  });

  it('sends Sign in to the sign-in tab, desktop and mobile', () => {
    expect(linksTo('Sign in')).toEqual(['/login?mode=login', '/login?mode=login']);
  });

  it('links to the Organisation Portal', () => {
    expect(linksTo('Organisation')).toEqual(['/organisation']);
  });

  it('no longer offers Try now', () => {
    expect(html).not.toContain('Try now');
  });

  it('shows the logo plainly, not as a highlighted button', () => {
    expect(html).not.toContain('brand-highlighted');
    expect(html).toContain('aria-label="Clyptusap.ai home"');
  });

  it('makes the logo shine with a decorative glint masked to the logo', () => {
    expect(html).toContain('brand-shine');
    expect(html).toMatch(/<span class="brand-shine-glint" aria-hidden="true" style="--logo-mask:url\([^)]+\)"/);
  });
});
