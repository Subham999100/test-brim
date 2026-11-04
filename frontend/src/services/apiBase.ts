/**
 * Where the browser sends API requests.
 *
 * Default "/api": the same origin as the page. The Vite dev server (`npm run dev`, `npm run preview`)
 * proxies /api to the backend on port 8000 (vite.config.ts), and in production the web container
 * (Caddy in docker-compose.prod.yml) proxies /api to the backend container.
 *
 * Set VITE_API_BASE_URL at build time only when the API is served from a different origin, for example
 * `https://api.example.com/api`. That origin must then be listed in the backend's ALLOWED_ORIGINS.
 */
export const DEFAULT_API_BASE_URL = '/api';

/** The configured base without trailing slashes, or the same-origin default when nothing is configured. */
export const resolveApiBaseUrl = (configured?: string | null): string => {
  const value = (configured ?? '').trim().replace(/\/+$/, '');
  return value || DEFAULT_API_BASE_URL;
};

export const API_BASE_URL = resolveApiBaseUrl(import.meta.env.VITE_API_BASE_URL as string | undefined);
