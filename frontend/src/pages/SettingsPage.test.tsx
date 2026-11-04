import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { SettingsPage } from './SettingsPage';

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'theme-user', name: 'Test' }, logout: vi.fn() }),
}));

afterEach(() => vi.unstubAllGlobals());

describe('Settings appearance', () => {
  it.each([
    [null, 'Light'],
    ['invalid', 'Light'],
    ['light', 'Light'],
    ['dark', 'Dark'],
    ['system', 'System'],
  ])('selects %s preference as %s', (saved, expected) => {
    const getItem = vi.fn(() => saved);
    vi.stubGlobal('localStorage', { getItem });
    const html = renderToStaticMarkup(<MemoryRouter><SettingsPage /></MemoryRouter>);
    // The key public/theme-init.js and AppLayout apply; a per-account key would be lost on reload,
    // because theme-init.js runs before anyone is signed in.
    expect(getItem).toHaveBeenCalledWith('clyptus-appearance');
    const selected = html.match(/<button class="appearance-option cursor-pointer selected"[^>]*>(.*?)<\/button>/)?.[1];
    expect(selected).toContain(`<span>${expected}</span>`);
  });
});
