import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}));

const { LandingPage } = await import('./LandingPage');

const render = () =>
  renderToStaticMarkup(
    <MemoryRouter initialEntries={['/']}>
      <LandingPage />
    </MemoryRouter>,
  );

describe('LandingPage', () => {
  it('shows the "What is Clyptus.AI" label without a section number', () => {
    const label = render().match(/<div class="intro-label">([\s\S]*?)<\/div>/)?.[1] ?? '';

    expect(label).toContain('WHAT IS CLYPTUS.AI');
    expect(label).not.toContain('section-index');
    expect(label).not.toMatch(/>\s*01\s*</);
  });
});
