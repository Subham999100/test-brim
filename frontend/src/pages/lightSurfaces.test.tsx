import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

const auth = vi.hoisted(() => ({
  user: { id: 'user-1', email: 'user@example.com', name: 'User', is_admin: false },
  token: 'test-token',
  loading: false,
  logout: vi.fn(),
  adminLogin: vi.fn(),
}));
vi.mock('../context/AuthContext', () => ({ useAuth: () => auth }));

const { AdminLoginPage } = await import('./admin/AdminLoginPage');
const { AdminProtectedRoute } = await import('../layouts/AdminProtectedRoute');
const { AssistantGuideModal } = await import('../components/ui/AssistantGuideModal');
const { RAGInspectorPanel } = await import('../components/chat/RAGInspectorPanel');
const { ShareModal } = await import('../components/chat/ShareModal');

const render = (element: React.ReactNode) => renderToStaticMarkup(<MemoryRouter>{element}</MemoryRouter>);

afterEach(() => {
  auth.loading = false;
  vi.unstubAllGlobals();
});

describe('light surfaces outside the main workspace', () => {
  it('renders the admin sign-in page and fields with light backgrounds and dark text', () => {
    vi.stubGlobal('window', { location: { search: '' } });
    const html = render(<AdminLoginPage />);
    expect(html).toContain('min-h-screen bg-white dark:bg-[#06070b]');
    expect(html).toContain('bg-white/90 dark:bg-[#0c0e14]/90');
    expect(html).toMatch(/<input[^>]*bg-white dark:bg-\[#12151f\][^>]*text-slate-900 dark:text-white/);
  });

  it('renders the admin loading screen in light mode', () => {
    auth.loading = true;
    const html = render(<AdminProtectedRoute><div>Admin content</div></AdminProtectedRoute>);
    expect(html).toContain('min-h-screen bg-white dark:bg-[#07090e]');
    expect(html).not.toContain('Admin content');
  });

  it('renders the admin access-denied screen in light mode without granting access', () => {
    const html = render(<AdminProtectedRoute><div>Admin content</div></AdminProtectedRoute>);
    expect(html).toContain('min-h-screen bg-white dark:bg-[#06080d]');
    expect(html).toContain('Administrator Privileges Required');
    expect(html).not.toContain('Admin content');
  });

  it('renders the Guide modal with light cards and readable text', () => {
    const html = render(<AssistantGuideModal isOpen onClose={vi.fn()} />);
    expect(html).toContain('bg-white dark:bg-[#09090f]');
    expect(html).toContain('text-slate-800 dark:text-slate-200');
  });

  it('renders the retrieval inspector with light search fields', () => {
    const html = render(<RAGInspectorPanel />);
    expect(html).toMatch(/<input[^>]*bg-white dark:bg-\[#111118\]/);
    expect(html).toContain('bg-white dark:bg-[#09090f]');
  });

  it('renders the chat-sharing dialog with a light surface', () => {
    vi.stubGlobal('window', { location: { origin: 'http://localhost:5173' } });
    const html = render(<ShareModal chat={{ id: 'chat-1', title: 'Test chat', user_id: 'user-1', created_at: '', updated_at: '' }} isOpen onClose={vi.fn()} />);
    expect(html).toContain('bg-slate-50 dark:bg-slate-900');
    expect(html).toContain('text-slate-900 dark:text-white');
  });
});
