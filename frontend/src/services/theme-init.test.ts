/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { describe, expect, it, vi } from 'vitest';

const script = readFileSync(new URL('../../public/theme-init.js', import.meta.url), 'utf8');

// The one-time light-default migration has already run in these browsers (theme.test.tsx covers it).
function initialize(preference: string | null, systemDark: boolean, storageBlocked = false) {
  const classes = new Set(['dark']);
  const getItem = vi.fn((key: string) => {
    if (storageBlocked) throw new Error('Storage blocked');
    return key === 'clyptus-light-default-v1' ? 'applied' : preference;
  });
  runInNewContext(script, {
    localStorage: { getItem },
    window: { matchMedia: () => ({ matches: systemDark }) },
    document: { documentElement: { classList: {
      add: (name: string) => classes.add(name),
      remove: (name: string) => classes.delete(name),
    } } },
  });
  if (!storageBlocked) expect(getItem).toHaveBeenCalledWith('clyptus-appearance');
  return classes.has('dark');
}

describe('theme before React starts', () => {
  it.each([false, true])('starts light without a preference, including system dark=%s', (systemDark) => {
    expect(initialize(null, systemDark)).toBe(false);
  });

  it.each([
    ['light', true, false],
    ['dark', false, true],
    ['system', true, true],
    ['system', false, false],
    ['invalid', true, false],
  ] as const)('honors preference %s with system dark=%s', (preference, systemDark, dark) => {
    expect(initialize(preference, systemDark)).toBe(dark);
  });

  it('falls back to light when storage is unavailable', () => {
    expect(initialize(null, true, true)).toBe(false);
  });

  it('ships light HTML before the startup script executes', () => {
    const html = readFileSync(new URL('../../index.html', import.meta.url), 'utf8');
    expect(html.match(/<html[^>]*>/)?.[0]).not.toContain('dark');
    expect(html).toContain('<meta name="theme-color" content="#ffffff"');
  });
});
