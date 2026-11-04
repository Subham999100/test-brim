import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from './api';
import { userStorageKey } from './userStorage';

const api = vi.hoisted(() => ({
  apiGetProjects: vi.fn(),
  apiCreateProject: vi.fn(),
  apiUpdateProject: vi.fn(),
  apiDeleteProject: vi.fn(),
}));
vi.mock('./api', async (importOriginal) => ({ ...(await importOriginal<typeof import('./api')>()), ...api }));

const { projectService } = await import('./projectService');

const server = (id: string, name: string, extra: Record<string, unknown> = {}) => ({
  id, name, description: null, is_pinned: false, created_at: '2026-11-04T10:00:00Z',
  updated_at: '2026-11-04T10:00:00Z', chat_count: 0, ...extra,
});

let store: Record<string, string>;
const KEY = userStorageKey('u1', 'projects');

beforeEach(() => {
  store = {};
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
  });
  vi.stubGlobal('window', { dispatchEvent: vi.fn() });
  api.apiGetProjects.mockResolvedValue([]);
  api.apiCreateProject.mockImplementation(async (body: { name: string }) => server(`s-${body.name}`, body.name));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

const local = (...projects: Array<Record<string, unknown>>) => {
  store[KEY] = JSON.stringify(projects);
};

describe('projectService: projects live on the server', () => {
  it('maps server projects to the shape the UI uses', async () => {
    api.apiGetProjects.mockResolvedValue([server('p1', 'Billing', { description: 'FI-CA', is_pinned: true, chat_count: 3 })]);
    expect(await projectService.list('u1')).toEqual([{
      id: 'p1', name: 'Billing', description: 'FI-CA', isPinned: true, chatCount: 3,
      createdAt: '2026-11-04T10:00:00Z', updatedAt: '2026-11-04T10:00:00Z',
    }]);
  });

  it('copies projects saved in this browser to the server once, oldest first, then forgets them', async () => {
    local(
      { id: 'proj_new', name: 'Newer', description: 'second', isPinned: true },
      { id: 'proj_brim_core', name: 'SAP BRIM Architecture', description: 'BRIM Billing, Invoicing and Charging integration flows.' },
      { id: 'proj_old', name: 'Older', isPinned: false },
    );

    await projectService.list('u1');
    await projectService.list('u1');

    expect(api.apiCreateProject.mock.calls.map(([body]) => body)).toEqual([
      { name: 'Older', description: undefined, is_pinned: false },
      { name: 'Newer', description: 'second', is_pinned: true },
    ]);
    expect(store[KEY]).toBeUndefined();
  });

  it('keeps projects that were not copied yet, so a failure is retried without duplicates', async () => {
    local({ id: 'b', name: 'Second' }, { id: 'a', name: 'First' });
    api.apiCreateProject
      .mockImplementationOnce(async () => server('s1', 'First'))
      .mockRejectedValueOnce(new Error('network down'));

    await projectService.list('u1');
    expect(JSON.parse(store[KEY]).map((p: { name: string }) => p.name)).toEqual(['Second']);

    await projectService.list('u1');
    expect(api.apiCreateProject.mock.calls.map(([body]) => body.name)).toEqual(['First', 'Second', 'Second']);
    expect(store[KEY]).toBeUndefined();
  });

  it('drops a saved project the server refuses as invalid instead of retrying it forever', async () => {
    local({ id: 'bad', name: '   ' }, { id: 'ok', name: 'Fine' });
    api.apiCreateProject.mockImplementation(async (body: { name: string }) => {
      if (!body.name.trim()) throw new ApiError('Invalid', 422);
      return server('s', body.name);
    });
    await projectService.list('u1');
    expect(store[KEY]).toBeUndefined();
  });

  it("copies only the signed-in account's saved projects", async () => {
    store[userStorageKey('u2', 'projects')] = JSON.stringify([{ id: 'x', name: 'Someone else' }]);
    local({ id: 'a', name: 'Mine' });
    await projectService.list('u1');
    expect(api.apiCreateProject.mock.calls.map(([body]) => body.name)).toEqual(['Mine']);
    expect(store[userStorageKey('u2', 'projects')]).toBeDefined();
  });

  it('copies an account-customised copy of the old sample', async () => {
    local({ id: 'proj_brim_core', name: 'My renamed architecture', isPinned: true });
    await projectService.list('u1');
    expect(api.apiCreateProject.mock.calls.map(([body]) => body)).toEqual([
      { name: 'My renamed architecture', description: undefined, is_pinned: true },
    ]);
  });

  it('announces changes so the sidebar and project page stay in step', async () => {
    api.apiUpdateProject.mockResolvedValue(server('p1', 'Renamed'));
    await projectService.update('p1', { name: 'Renamed', isPinned: true });
    expect(api.apiUpdateProject).toHaveBeenCalledWith('p1', { name: 'Renamed', is_pinned: true });
    expect(window.dispatchEvent).toHaveBeenCalled();
  });
});
