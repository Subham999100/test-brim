/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: null, logout: vi.fn() }),
}));

const { SettingsPage } = await import('./SettingsPage');
const bootstrap = readFileSync(new URL('../../public/theme-init.js', import.meta.url), 'utf8');

afterEach(() => vi.unstubAllGlobals());

describe('theme before React renders', () => {
  it.each([
    [null, true, false],
    ['invalid', true, false],
    ['light', true, false],
    ['dark', false, true],
    ['system', true, true],
    ['system', false, false],
  ])('resolves preference %s with system dark=%s to dark=%s', (saved, systemDark, expectedDark) => {
    const classes = new Set(['dark']);
    runInNewContext(bootstrap, {
      localStorage: { getItem: (key: string) => key === 'clyptus-light-default-v1' ? 'applied' : saved },
      window: { matchMedia: () => ({ matches: systemDark }) },
      document: { documentElement: { classList: {
        add: (name: string) => classes.add(name),
        remove: (name: string) => classes.delete(name),
      } } },
    });
    expect(classes.has('dark')).toBe(expectedDark);
  });

  it.each(['dark', 'system', null])('switches legacy preference %s to light once', (saved) => {
    const storage = new Map<string, string>();
    if (saved) storage.set('clyptus-appearance', saved);
    const classes = new Set(['dark']);
    const context = {
      localStorage: {
        getItem: (key: string) => storage.get(key) ?? null,
        setItem: (key: string, value: string) => storage.set(key, value),
      },
      window: { matchMedia: () => ({ matches: true }) },
      document: { documentElement: { classList: {
        add: (name: string) => classes.add(name),
        remove: (name: string) => classes.delete(name),
      } } },
    };
    runInNewContext(bootstrap, context);
    expect(classes.has('dark')).toBe(false);
    expect(storage.get('clyptus-appearance')).toBe('light');
    storage.set('clyptus-appearance', 'dark');
    runInNewContext(bootstrap, context);
    expect(classes.has('dark')).toBe(true);
    expect(storage.get('clyptus-appearance')).toBe('dark');
  });

  it('falls back to light when browser storage is unavailable', () => {
    const remove = vi.fn();
    runInNewContext(bootstrap, {
      localStorage: { getItem: () => { throw new Error('Storage blocked'); } },
      document: { documentElement: { classList: { remove } } },
    });
    expect(remove).toHaveBeenCalledWith('dark');
  });

  it('starts the HTML shell in light mode before the bootstrap script runs', () => {
    const html = readFileSync(new URL('../../index.html', import.meta.url), 'utf8');
    expect(html).toContain('<html lang="en">');
    expect(html).toContain('name="theme-color" content="#ffffff"');
  });
});

describe('appearance settings', () => {
  it.each([
    [null, 'Light'],
    ['invalid', 'Light'],
    ['light', 'Light'],
    ['dark', 'Dark'],
    ['system', 'System'],
  ])('selects %s as %s', (saved, selected) => {
    vi.stubGlobal('localStorage', { getItem: () => saved });
    const html = renderToStaticMarkup(<MemoryRouter><SettingsPage /></MemoryRouter>);
    expect(html).toMatch(new RegExp(`class="appearance-option cursor-pointer selected"[^>]*>.*?<span>${selected}</span>`));
    expect(html.match(/appearance-option cursor-pointer selected/g)).toHaveLength(1);
  });
});
