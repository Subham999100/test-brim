import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearAllUserStorage, clearLegacyUserStorage, clearUserStorage, userStorageKey } from './userStorage';
import { projectService } from './projectService';

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

describe('user-scoped browser storage', () => {
  it('isolates each account project data', () => {
    projectService.createProject('user one', 'Private project');
    expect(projectService.getProjects('user two')).toEqual([]);
    expect(projectService.getProjects('user one').map((project) => project.name)).toContain('Private project');
  });

  it('starts new profiles without shared sample projects or automatic pins', () => {
    expect(projectService.getProjects('one')).toEqual([]);
    expect(projectService.getProjects('two')).toEqual([]);
  });

  it('keeps project pins, updates and deletion within the owning account', () => {
    const project = projectService.createProject('one', 'Private project');
    projectService.updateProject('one', project.id, { isPinned: true });
    expect(projectService.getProjects('one')).toEqual([expect.objectContaining({ name: 'Private project', isPinned: true })]);
    expect(projectService.getProjects('two')).toEqual([]);
    expect(() => projectService.updateProject('two', project.id, { name: 'Other account' })).toThrow('Project not found');
    projectService.deleteProject('two', project.id);
    expect(projectService.getProjects('one')[0].name).toBe('Private project');
    projectService.deleteProject('one', project.id);
    expect(projectService.getProjects('one')).toEqual([]);
  });

  it('hides the old untouched sample without removing custom projects or their stored data', () => {
    const stored = [
      { id: 'proj_brim_core', name: 'SAP BRIM Architecture', description: 'BRIM Billing, Invoicing and Charging integration flows.', isPinned: true },
      { id: 'private', name: 'My SAP project', isPinned: true },
    ];
    localStorage.setItem(userStorageKey('one', 'projects'), JSON.stringify(stored));
    expect(projectService.getProjects('one')).toEqual([stored[1]]);
    expect(JSON.parse(localStorage.getItem(userStorageKey('one', 'projects'))!)).toEqual(stored);
    expect(projectService.getProjects('two')).toEqual([]);
  });

  it('preserves an account-customised copy of the old sample', () => {
    const custom = { id: 'proj_brim_core', name: 'My renamed architecture', isPinned: true };
    localStorage.setItem(userStorageKey('one', 'projects'), JSON.stringify([custom]));
    expect(projectService.getProjects('one')).toEqual([custom]);
  });

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
