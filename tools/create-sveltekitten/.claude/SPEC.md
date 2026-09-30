# Template Improvement Spec

## Decisions
- Login identifier: **username** (both templates)
- Protected route group name: **(protected)** (both templates)

---

## SSR Template (`templates/ssr/`)

### Remove
- `src/lib/components/api-detail.svelte` — empty placeholder
- `src/lib/components/app-container.svelte` — trivial flex wrapper
- `src/lib/utils/cookies.ts` — `createCookieOptions()` unused
- `src/lib/api/api.ts` — generic REST client redundant with openapi-fetch

### Add
- `src/routes/+error.svelte` — basic error page
- `src/lib/features/health/api.ts` — typed GET /v1/health call via fastapiClient
- `src/lib/features/health/queries.ts` — `useHealthStatus()` TanStack Query hook
- `src/routes/login/+page.ts` — redirect to /home if already authenticated (server-side check via cookies)

### Modify
- `src/lib/features/login/schema.ts` — change `email` field → `username` (z.string().min(1))
- `src/lib/features/login/components/form.svelte` — change email input → username input (type="text")
- `src/routes/login/+page.server.ts` — `form.data.email` → `form.data.username` in API call body
- `src/routes/+layout.ts` — remove `enabled: browser` from QueryClient defaultOptions
- `src/routes/(auth)/` → rename directory to `src/routes/(protected)/`
- `src/lib/utils/auth.ts` `isProtectedRoute()` — update string check from `"(auth)"` → `"(protected)"`
- `src/routes/(protected)/home/+page.svelte` — replace placeholder text with health status widget (mirror SPA root +page.svelte pattern: useHealthStatus query, status indicator card)
- `.vscode/mcp.json` — switch from npx stdio to HTTP: `{ "svelte-mcp-server": { "url": "https://mcp.svelte.dev/mcp", "type": "http" } }`
- `agent-role.md` — update: (auth)→(protected), remove mention of api.ts, update adapter to node, fix feature structure paths

---

## SPA Template (`templates/spa/`)

### Remove
- `src/lib/components/api-detail.svelte` — empty placeholder
- `src/lib/components/app-container.svelte` — trivial flex wrapper
- `src/lib/utils/cookies.ts` — server cookie utilities, unused in SPA
- `src/lib/utils/auth.ts` — server cookie utilities, unused in SPA
- All Capacitor mobile comments (`// [CapacitorJS]` blocks) from:
  - `src/lib/api/auth-interceptor.ts`
  - `src/lib/stores/auth.svelte.ts`
- All `console.log` / `console.error` / `console.warn` statements from:
  - `src/lib/api/auth-interceptor.ts`
  - `src/lib/guards/auth.ts`
  - `src/lib/stores/auth.svelte.ts`
  - `src/routes/(guard)/+layout.ts`

### Add
- `src/routes/+error.svelte` — basic error page
- `src/routes/login/+page.ts` — call `redirectIfAuthenticated()` from `$lib/guards/auth`

### Modify
- `src/routes/(guard)/` → rename directory to `src/routes/(protected)/`
- `src/routes/(protected)/+layout.ts` — fix import paths after rename, remove all console.logs, remove Capacitor comments, keep requireAuth() call and return values
- `src/lib/api/client.ts` — add openapi-fetch `RequestMiddleware` that injects `Authorization: Bearer {token}` header from `authStore.accessToken` when present
- `src/lib/features/me/queries.ts` — remove manual `Authorization` header injection (now handled by client middleware)
- `src/lib/api/auth-interceptor.ts` — change `ensureValidToken` buffer from `540` → `120` seconds
- `src/routes/+layout.ts` — add `export async function load()` that creates and returns QueryClient (staleTime: 60000, retry: 1)
- `src/routes/+layout.svelte` — remove inline QueryClient creation, receive `data` prop, use `data.queryClient`; remove unused `browser` import
- `agent-role.md` — update: (guard)→(protected)
