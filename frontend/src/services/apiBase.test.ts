/// <reference types="node" />
import { readFileSync } from 'node:fs';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { API_BASE_URL, DEFAULT_API_BASE_URL, resolveApiBaseUrl } from './apiBase';
import { apiGetChats, apiGetDocuments } from './api';

afterEach(() => vi.unstubAllGlobals());

const stubFetch = (body: unknown) => {
  const fetchMock = vi.fn(async () => new Response(JSON.stringify(body), { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
  vi.stubGlobal('localStorage', { getItem: () => null, setItem: () => undefined, removeItem: () => undefined });
  return fetchMock;
};

const requestedUrl = (fetchMock: ReturnType<typeof stubFetch>) =>
  (fetchMock.mock.calls[0] as unknown as [string])[0];

describe('API base URL (deployment)', () => {
  it('defaults to the same-origin /api path, so any deployed host works without a rebuild', () => {
    expect(DEFAULT_API_BASE_URL).toBe('/api');
    expect(resolveApiBaseUrl(undefined)).toBe('/api');
    expect(resolveApiBaseUrl(null)).toBe('/api');
    expect(resolveApiBaseUrl('')).toBe('/api');
    expect(resolveApiBaseUrl('   ')).toBe('/api');
  });

  it('uses a configured VITE_API_BASE_URL without trailing slashes', () => {
    expect(resolveApiBaseUrl('https://api.example.com/api')).toBe('https://api.example.com/api');
    expect(resolveApiBaseUrl('https://api.example.com/api/')).toBe('https://api.example.com/api');
    expect(resolveApiBaseUrl(' /backend/api// ')).toBe('/backend/api');
  });

  it('is not configured in the test build, so requests stay relative', () => {
    expect(API_BASE_URL).toBe('/api');
  });

  it('no source file hard-codes the development backend address any more', () => {
    for (const file of ['./api.ts', './apiBase.ts', '../components/chat/RAGInspectorPanel.tsx']) {
      const source = readFileSync(new URL(file, import.meta.url), 'utf-8');
      expect(source, file).not.toContain('localhost:8000');
    }
  });
});

describe('query strings built without new URL()', () => {
  it('lists chats with search and project filters', async () => {
    const fetchMock = stubFetch([]);
    await apiGetChats('dunning run', 'p1');
    expect(requestedUrl(fetchMock)).toBe('/api/chats?search=dunning+run&project_id=p1');
  });

  it('lists all chats without a query string', async () => {
    const fetchMock = stubFetch([]);
    await apiGetChats();
    expect(requestedUrl(fetchMock)).toBe('/api/chats');
  });

  it('keeps the document filters: status "all", empty search and page 0 are left out', async () => {
    const fetchMock = stubFetch({ documents: [], total: 0 });
    await apiGetDocuments({ status: 'all', search: '', page: 0, page_size: 0 });
    expect(requestedUrl(fetchMock)).toBe('/api/documents');
  });

  it('sends the document filters that are set', async () => {
    const fetchMock = stubFetch({ documents: [], total: 0 });
    await apiGetDocuments({ status: 'failed', search: 'billing', page: 2, page_size: 50 });
    expect(requestedUrl(fetchMock)).toBe('/api/documents?status=failed&search=billing&page=2&page_size=50');
  });
});
