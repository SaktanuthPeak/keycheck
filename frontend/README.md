# create-sveltekitten

Scaffold a SvelteKit project with opinionated defaults for SSR or SPA.

## Usage

```bash
pnpx github:importstar/create-sveltekitten
```

The CLI will prompt for:

1. **Project name** — used as the folder name and `package.json` name
2. **Template** — SSR or SPA (see below)
3. **Backend base URL** — default `http://localhost:9000`

Then run:

```bash
cd <project-name>
pnpm install
pnpm dev
```

## Templates

### SSR

Server-side rendering via `adapter-node`.

| What      | Detail                                                  |
| --------- | ------------------------------------------------------- |
| Adapter   | `@sveltejs/adapter-node`                                |
| Auth      | Server-side, cookie-based                               |
| API proxy | SvelteKit server routes forward to backend              |
| Logger    | `pino` + `pino-pretty`                                  |
| API types | `openapi-typescript` → `src/lib/api/paths/fastapi.d.ts` |

**Environment variables (`.env`)**

```
PUBLIC_APP_TITLE=my-app
BACKEND_API_URL=http://localhost:9000
```

**After backend changes** — regenerate OpenAPI types:

```bash
pnpm openapi:fastapi
```

---

### SPA

Static output via `adapter-static`. Auth and API calls handled entirely client-side.

| What          | Detail                                            |
| ------------- | ------------------------------------------------- |
| Adapter       | `@sveltejs/adapter-static`                        |
| Auth          | Client-side, JWT stored in memory                 |
| Data fetching | TanStack Query v6                                 |
| API types     | `openapi-typescript` → `src/lib/api/openapi.d.ts` |

**Environment variables (`.env`)**

```
PUBLIC_APP_TITLE=my-app
PUBLIC_API_URL=http://localhost:9000
```

**After backend changes** — regenerate OpenAPI types:

```bash
pnpm openapi
```

---

## Common stack (both templates)

- SvelteKit 2 · Svelte 5
- TypeScript 6
- TailwindCSS 4
- bits-ui · shadcn-svelte components
- superforms + zod
- openapi-fetch for type-safe API calls
- ESLint + Prettier

## Feature architecture

Every domain feature lives in `src/lib/features/<name>/`, structured so it stays swappable and testable:

| File | Purpose |
| --- | --- |
| `schema.ts` | Zod schemas + inferred TypeScript types |
| `port.ts` | Interface for the feature's API surface (e.g. `ItemsApi`) — `queries.ts` depends on this, not on `api.ts` directly |
| `api.ts` | Concrete client implementation of the port (HTTP calls, or an in-memory mock for SPA examples) |
| `server.ts` *(SSR full-stack only)* | Repository: raw Drizzle queries, no business rules |
| `service.ts` *(SSR full-stack only)* | Use-case layer between the route and the repository — this is where authorization/business rules live (e.g. verifying a row belongs to the requesting user) |
| `queries.ts` | TanStack Query key factory + hooks, defaulting to the real port implementation but overridable (e.g. for tests) |
| `components/` | Feature UI |

`src/lib/features/items/` is the reference implementation of this pattern in both templates — SSR's version additionally shows the `service.ts` layer enforcing per-item ownership before a route handler is allowed to mutate or delete it.

## Scripts

| Script        | Description                    |
| ------------- | ------------------------------ |
| `pnpm dev`    | Dev server on `0.0.0.0`        |
| `pnpm build`  | Production build               |
| `pnpm check`  | Type-check with `svelte-check` |
| `pnpm lint`   | Prettier + ESLint              |
| `pnpm format` | Auto-format                    |
