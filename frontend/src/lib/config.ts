import * as publicEnv from '$env/static/public';

// Spread so missing optional vars resolve to undefined instead of failing the build.
const env: Record<string, string | undefined> = { ...publicEnv };

/** API origin; '' = same origin (Vite dev proxy / reverse proxy in front of the backend). */
export const API_ORIGIN = (env.PUBLIC_API_URL ?? '').replace(/\/+$/, '');
export const API_BASE = `${API_ORIGIN}/api/v1`;
/** In-browser simulated API (Spec §17.3: results must be labelled as simulated). */
export const USE_MOCK = env.PUBLIC_USE_MOCK === '1' || env.PUBLIC_USE_MOCK === 'true';
export const APP_TITLE = env.PUBLIC_APP_TITLE || 'KeyCheck';

/** Client-side pre-checks mirroring backend defaults (docs/api-contract.md §4). */
export const MAX_UPLOAD_BYTES = 15 * 1024 * 1024;
export const POLL_INTERVAL_MS = 1500;
