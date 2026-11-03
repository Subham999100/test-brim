import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { TokenMeterBadge } from './TokenMeterBadge';
import { TokenSavedToast } from './TokenSavedToast';
import { formatTokens, savingsMessage } from './tokenSavings';

const SAVED = { used: 900, baseline: 4000, saved: 3100 };
const NOTHING_SAVED = { used: 700, baseline: 500, saved: 0 };

describe('savingsMessage', () => {
  it('tells the user how many tokens they saved compared with other AI chatbots, not how many were used', () => {
    const message = savingsMessage(SAVED);

    expect(message.saved).toBe(true);
    expect(message.emoji).toBe('😊');
    expect(message.title).toBe('You saved ~3,100 tokens!');
    expect(message.detail).toBe("That's 78% fewer than other AI chatbots would use for this question.");
    expect(`${message.title} ${message.detail}`).not.toContain('900');
  });

  it('shows small savings as they are, never rounded down to 0%', () => {
    const message = savingsMessage({ used: 9980, baseline: 10000, saved: 20 });

    expect(message.title).toBe('You saved ~20 tokens!');
    expect(message.detail).toContain('1% fewer');
    expect(savingsMessage({ used: 9, baseline: 10, saved: 1 }).title).toBe('You saved ~1 token!');
  });

  it('says no tokens were saved instead of showing 0', () => {
    const message = savingsMessage(NOTHING_SAVED);

    expect(message.saved).toBe(false);
    expect(message.title).toBe('No tokens saved for this question.');
    expect(`${message.title} ${message.detail}`).not.toMatch(/\d/);
  });

  it('formats whole, non-negative token counts', () => {
    expect(formatTokens(12345.6)).toBe('12,346');
    expect(formatTokens(-3)).toBe('0');
  });
});

describe('TokenMeterBadge', () => {
  it('shows a saving-in-progress indicator without numbers while the answer streams', () => {
    const html = renderToStaticMarkup(<TokenMeterBadge streaming />);

    expect(html).toContain('😊');
    expect(html).toContain('Saving tokens…');
    expect(html).not.toContain('~');
    expect(html).not.toContain('Saved');
  });

  it('shows only the tokens saved once the answer is complete', () => {
    const html = renderToStaticMarkup(<TokenMeterBadge usage={SAVED} />);

    expect(html).toContain('aria-label="Saved ~3,100 tokens"');
    expect(html).toContain('Saved ~1 token<');
    expect(html).not.toContain('~0');
    expect(html).not.toContain('900');
  });

  it('shows nothing when nothing was saved', () => {
    expect(renderToStaticMarkup(<TokenMeterBadge usage={NOTHING_SAVED} />)).toBe('');
    expect(renderToStaticMarkup(<TokenMeterBadge />)).toBe('');
  });
});

describe('TokenSavedToast', () => {
  it('pops up with the savings of the completed answer', () => {
    const html = renderToStaticMarkup(<TokenSavedToast usage={SAVED} onClose={() => {}} />);

    expect(html).toContain('role="status"');
    expect(html).toContain('You saved ~3,100 tokens!');
  });

  it('pops up after every answer, saying so when no tokens were saved', () => {
    const html = renderToStaticMarkup(<TokenSavedToast usage={NOTHING_SAVED} onClose={() => {}} />);

    expect(html).toContain('No tokens saved for this question.');
    expect(html).not.toMatch(/>0</);
  });

  it('does not pop up before an answer completes', () => {
    expect(renderToStaticMarkup(<TokenSavedToast usage={null} onClose={() => {}} />)).toBe('');
  });
});
