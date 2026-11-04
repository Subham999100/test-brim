import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, describe, expect, it, vi } from 'vitest';

// Owner decision 2026-11-04: creating an account does not sign the user in; they sign in afterwards.
const api = vi.hoisted(() => ({
  apiRegister: vi.fn(),
  setStoredToken: vi.fn(),
}));

vi.mock('../services/api', () => ({
  ApiError: class ApiError extends Error {},
  apiGetMe: vi.fn(),
  apiLogout: vi.fn(),
  apiLogin: vi.fn(),
  apiAdminLogin: vi.fn(),
  apiOrgLogin: vi.fn(),
  apiRegister: api.apiRegister,
  getStoredToken: () => null,
  setStoredToken: api.setStoredToken,
  clearStoredToken: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
  TOKEN_STORAGE_KEY: 'test-token-key',
}));

const { AuthProvider, useAuth } = await import('./AuthContext');

const captureAuth = () => {
  const onAuth = vi.fn<(auth: ReturnType<typeof useAuth>) => void>();
  const Capture = () => {
    onAuth(useAuth());
    return null;
  };
  renderToStaticMarkup(
    <AuthProvider>
      <Capture />
    </AuthProvider>,
  );
  return onAuth.mock.calls[0][0];
};

describe('AuthContext.register', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it('creates the account without starting a session', async () => {
    const stored = new Map<string, string>();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => void stored.set(key, value),
      removeItem: (key: string) => void stored.delete(key),
      key: (index: number) => [...stored.keys()][index] ?? null,
      get length() {
        return stored.size;
      },
      clear: () => stored.clear(),
    });
    // What the server returned before the change; the client must not use a token even if one arrives.
    api.apiRegister.mockResolvedValue({
      access_token: 'server-token',
      token_type: 'bearer',
      user: { id: 'u1', email: 'new@example.com', name: 'New Person' },
      id: 'u1',
      email: 'new@example.com',
      name: 'New Person',
    });

    await captureAuth().register('New Person', 'new@example.com', 'abcd1234');

    expect(api.apiRegister).toHaveBeenCalledWith('New Person', 'new@example.com', 'abcd1234');
    expect(api.setStoredToken).not.toHaveBeenCalled();
    expect(stored.size).toBe(0);
  });

  it('passes a sign-up failure through so the form can show it', async () => {
    api.apiRegister.mockRejectedValue(new Error('Registration could not be completed.'));

    await expect(captureAuth().register('New Person', 'taken@example.com', 'abcd1234')).rejects.toThrow(
      'Registration could not be completed.',
    );
    expect(api.setStoredToken).not.toHaveBeenCalled();
  });
});
