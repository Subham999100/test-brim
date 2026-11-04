import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearAllUserStorage, clearLegacyUserStorage, clearUserStorage, userStorageKey } from './userStorage';

const values = new Map<string, string>();

beforeEach(() => {
  values.clear();
  vi.stubGlobal('localStorage', {
    get length() { return values.size; },
    key: (index: number) => [...values.keys()][index] ?? null,
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => values.set(key, value),
    removeItem: (key: string) => values.delete(key),
  });
});

afterEach(() => vi.unstubAllGlobals());

// Projects moved to the server (2026-11-04); their account isolation is tested in backend/tests/test_projects.py
// and the one-time copy of browser-saved projects in projectService.test.ts.
describe('user-scoped browser storage', () => {
  it('keeps pinned chat ids scoped to each account and ignores global legacy pins', () => {
    localStorage.setItem(userStorageKey('one', 'pinned_chats'), JSON.stringify(['chat-one']));
    localStorage.setItem(userStorageKey('two', 'pinned_chats'), JSON.stringify(['chat-two']));
    localStorage.setItem('clyptus_pinned_chats', JSON.stringify(['chat-one']));
    clearLegacyUserStorage();
    expect(JSON.parse(localStorage.getItem(userStorageKey('one', 'pinned_chats'))!)).toEqual(['chat-one']);
    expect(JSON.parse(localStorage.getItem(userStorageKey('two', 'pinned_chats'))!)).toEqual(['chat-two']);
    expect(localStorage.getItem(userStorageKey('three', 'pinned_chats'))).toBeNull();
    expect(localStorage.getItem('clyptus_pinned_chats')).toBeNull();
  });

  it('clears only the current user on logout', () => {
    localStorage.setItem(userStorageKey('one', 'projects'), '[]');
    localStorage.setItem(userStorageKey('one', 'profile'), '{}');
    localStorage.setItem(userStorageKey('two', 'projects'), '["private"]');
    localStorage.setItem('clyptus_projects', '["legacy"]');

    clearUserStorage('one');
    clearLegacyUserStorage();

    expect(localStorage.getItem(userStorageKey('one', 'profile'))).toBeNull();
    expect(localStorage.getItem(userStorageKey('two', 'projects'))).toBe('["private"]');
    expect(localStorage.getItem('clyptus_projects')).toBeNull();
  });

  it('clears all account-scoped data after an invalid session', () => {
    localStorage.setItem(userStorageKey('one', 'projects'), '[]');
    localStorage.setItem(userStorageKey('two', 'profile'), '{}');
    clearAllUserStorage();
    expect(values.size).toBe(0);
  });
});
