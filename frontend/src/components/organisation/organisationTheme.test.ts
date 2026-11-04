/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const css = readFileSync(new URL('./organisation.css', import.meta.url), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const rules = [...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].flatMap(([, selectors, declarations]) =>
  selectors.split(',').map((selector) => ({ selector: selector.trim(), declarations })),
);

describe('organisation sign-in background', () => {
  it('has no grey dot texture behind the sign-in pages', () => {
    const backgrounds = rules.filter(({ selector }) => selector.includes('.auth-split-org'));
    for (const { declarations } of backgrounds) expect(declarations).not.toMatch(/radial-gradient\(1px/);
  });
});

describe('admin Accounts panel theme', () => {
  it('keeps console-specific dark palette overrides behind the dark theme selector', () => {
    const palettes = rules.filter(({ selector, declarations }) => selector.includes('.org-console') && /--surface\s*:/.test(declarations));
    expect(palettes.length).toBeGreaterThan(0);
    for (const { selector } of palettes) expect(selector).toMatch(/^\.dark /);
    expect(rules.find(({ selector }) => selector === '.org-console')?.declarations).toContain('color:var(--text)');
  });

  it('scopes console-specific status and form colours to dark mode too', () => {
    const overrides = rules.filter(({ selector }) => /\.org-console\s+\.org-/.test(selector));
    expect(overrides.length).toBeGreaterThan(0);
    for (const { selector } of overrides) expect(selector).toMatch(/^\.dark /);
  });

  it('uses the inherited light/dark tokens for panel, table header and search field surfaces', () => {
    for (const selector of ['.org-panel', '.org-table th', '.org-search input']) {
      const declarations = rules.find((rule) => rule.selector === selector)?.declarations;
      expect(declarations).toMatch(/background:var\(--(?:surface|raised)\)/);
    }
  });
});
