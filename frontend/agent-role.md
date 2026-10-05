# Agent Role: SvelteKit Frontend Agent (SPA)

> KeyCheck note: the template's login/auth (`authStore`, `auth-interceptor`, `(protected)` routes) and the `items` example were removed. There is no auth; sections below that mention them are historical. The canonical feature is `src/lib/features/inspection/` (see README.md).

You are a frontend subagent working on a SvelteKit web application built from the **sveltekitten** SPA template. Your job is to implement, modify, and debug frontend features while respecting the conventions of this template.

## Tech Stack

- **SvelteKit v2** + **Svelte 5** (runes mode) + **Vite 8**, deployed via `@sveltejs/adapter-static`
- **TypeScript** throughout
- **Tailwind CSS v4** (via `@tailwindcss/vite` plugin — no separate config file)
- **bits-ui** as the headless primitive layer; shadcn-style components in `src/lib/components/ui/`
- **TanStack Query** (`@tanstack/svelte-query`) for client-side data fetching & mutations — `QueryClientProvider` is wired in the root layout
- **Superforms + Zod** for forms
- **openapi-fetch** typed against `src/lib/api/openapi.d.ts` for backend calls
- **svelte-sonner** for toast notifications (placed in root layout)

## What You Can Do

- Add new routes under `src/routes/` using SvelteKit file-based routing
- Add pages that require authentication inside the `(protected)` route group — the auth guard runs automatically via `+layout.ts`
- Build UI components in `src/lib/components/ui/` following the existing `component.svelte` + `index.ts` pattern
- Add new features under `src/lib/features/<feature-name>/` with `api.ts`, `queries.ts`, `schema.ts`, and `components/`
- Call backend APIs through the typed `client` from `$lib/api/client.ts` — uses `openapi-fetch` with `PUBLIC_API_URL`
- Use `fetchWithAuth` from `$lib/api/auth-interceptor.ts` for authenticated requests with automatic token refresh
- Use `authStore` from `$lib/stores/auth.svelte.ts` for client-side auth state

## Feature Structure Pattern

Every domain feature is completely self-contained in `src/lib/features/<feature-name>/`:

```text
src/lib/features/<feature-name>/
├── schema.ts           # Zod schemas (input validation) & inferred TypeScript types
├── port.ts             # Interface for the feature's API surface (e.g. `ItemsApi`)
├── api.ts              # Typed API calls via client (or mock fallback) — implements port.ts
├── queries.ts          # TanStack Query key factory + use<Query>/use<Mutation> hooks, injected with the port
├── components/         # Feature-specific Svelte 5 components
└── index.ts            # Public barrel export
```

**Why `port.ts`?** `queries.ts` depends on the `port.ts` interface instead of importing `api.ts` directly (dependency inversion). Each hook takes the implementation as an optional parameter defaulting to the real one, e.g. `useItems(initialDataGetter?, itemsApi: ItemsApi = defaultItemsApi)` — swap it for a fake in tests without touching `queries.ts`.

### Canonical Reference Example
- `src/lib/features/items/` — Reference CRUD feature demonstrating schemas, the `ItemsApi` port, an in-memory mock implementation, query key factories, mutations, optimistic updates, and toasts.
- `src/routes/(protected)/items/` — Client-side route demonstrating reactive TanStack Query state handling.

### How to Erase / Replace the Example Feature
1. Delete the feature: `rm -rf src/lib/features/items`
2. Delete the route: `rm -rf src/routes/(protected)/items`
3. Remove the `<a href="/items">Items</a>` link in `src/routes/(protected)/+layout.svelte`.

## Key Constraints

- **SPA mode — no server-side load functions** — all data fetching is client-side via TanStack Query
- **Auth is client-side** — `authStore` holds the access token in memory; refresh token is in an httpOnly cookie
- **Protected pages must live inside `(protected)/`** — the layout guard calls `requireAuth()` automatically
- **Svelte 5 runes only** — no legacy Svelte 4 syntax. See the table below.
- **Run `svelte-autofixer` before finalizing any `.svelte` file**:
  ```bash
  npx @sveltejs/mcp svelte-autofixer ./src/path/to/Component.svelte
  ```
- **Type-check before finishing**: `pnpm check`

## Svelte 5 Quick Reference

| Avoid | Use |
|---|---|
| `let x = 0` (implicit reactivity) | `$state` |
| `$:` reactive statements | `$derived` / `$effect` |
| `export let` | `$props` |
| `on:click` | `onclick` |
| `<slot>` | `{#snippet}` + `{@render}` |
| `<svelte:component this={X}>` | `<X>` |
| `use:action` | `{@attach}` |
| Svelte stores for shared state | class with `$state` fields |

- Use `$state.raw` for large API response objects (avoids deep proxy overhead)
- Derive computed values with `$derived`; never compute inside `$effect`
- Always key `{#each}` blocks — never use array index as key
- Use `createContext` (not `setContext`/`getContext`) for type-safe context

## Adding a New Feature — Checklist

1. **Schema**: Create `src/lib/features/your-feature/schema.ts` with Zod validation schemas and exported types.
2. **Port**: Create `src/lib/features/your-feature/port.ts` with an interface describing the feature's API surface.
3. **API**: Create `src/lib/features/your-feature/api.ts` with typed endpoint functions implementing the `port.ts` interface.
4. **Queries**: Create `src/lib/features/your-feature/queries.ts` with query key factory and custom query/mutation hooks, each taking the port implementation as an optional parameter (default to the real `api.ts` implementation).
5. **Components**: Build UI in `src/lib/features/your-feature/components/` using primitives from `$lib/components/ui/` and `toast` from `svelte-sonner`.
6. **Route**: Create `src/routes/(protected)/your-feature/+page.svelte`.
7. **Navigation**: Add route link in `src/routes/(protected)/+layout.svelte`.
8. **Validate**: Run `npx @sveltejs/mcp svelte-autofixer` on `.svelte` files and verify with `pnpm check`.

## Out of Scope

- Adding server-side load functions or `+page.server.ts` files (this is a static SPA)
- Modifying the auth interceptor token refresh logic in `$lib/api/auth-interceptor.ts`
- Changing cookie names or TTLs in `$lib/utils/auth.ts`
- Regenerating OpenAPI types (`pnpm openapi` — do this only if the task explicitly requires it)
