import { describe, expect, it } from 'vitest';
import { revealStep } from './reveal';

describe('revealStep: how many characters the typewriter shows per tick', () => {
  it('keeps the existing pacing while the tab is visible', () => {
    expect(revealStep(400, false)).toBe(100);
    expect(revealStep(100, false)).toBe(6);
    expect(revealStep(20, false)).toBe(3);
    expect(revealStep(10, false)).toBe(2);
    expect(revealStep(3, false)).toBe(1);
  });

  it('shows everything at once in a background tab, where browsers slow timers to once a second or less', () => {
    expect(revealStep(4000, true)).toBe(4000);
    expect(revealStep(1, true)).toBe(1);
  });
});
