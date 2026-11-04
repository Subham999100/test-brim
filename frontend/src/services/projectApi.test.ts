import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiCreateChat, apiGetChats } from './api';

afterEach(() => vi.unstubAllGlobals());

const stubFetch = (body: unknown) => {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(body), { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => undefined, removeItem: () => undefined });
  return fetchMock;
};

describe('chats inside projects', () => {
  it('creates a chat in a project', async () => {
    const fetchMock = stubFetch({ id: 'c1', title: 'Q', project_id: 'p1' });
    await apiCreateChat('Q', 'p1');
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({ title: 'Q', project_id: 'p1' });
  });

  it('creates an ordinary chat without a project', async () => {
    const fetchMock = stubFetch({ id: 'c1', title: 'Q' });
    await apiCreateChat('Q');
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(JSON.parse(String(init.body))).toEqual({ title: 'Q' });
  });

  it("lists only a project's chats when asked", async () => {
    const fetchMock = stubFetch([]);
    await apiGetChats(undefined, 'p1');
    const [url] = fetchMock.mock.calls[0] as unknown as [string];
    expect(new URL(url).searchParams.get('project_id')).toBe('p1');
  });
});
