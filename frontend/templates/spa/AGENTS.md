# Agent Instructions — SPA Template

## Start Here

Before doing any work, read `agent-role.md` in this directory. It contains the full project context: tech stack, auth pattern, feature structure, key constraints, and a new-feature checklist.

## Available Skills

Three skills are installed in `.agents/skills/`. Use them via your skill system:

- **svelte-core-bestpractices** — Svelte 5 runes patterns, snippets, reactivity rules. Use whenever writing or reviewing `.svelte` files.
- **svelte-code-writer** — Opinionated code generation for Svelte 5. Use when scaffolding new components or routes.
- **shadcn-svelte** — Pre-built shadcn-svelte component catalog. Use when adding UI components from `src/lib/components/ui/`.

## Svelte MCP Tools

You have access to the Svelte MCP server for live Svelte 5 / SvelteKit documentation.

### 1. list-sections
Use this FIRST to discover available documentation sections.
When asked about Svelte or SvelteKit topics, ALWAYS call this before answering.

### 2. get-documentation
Fetches full documentation for specific sections.
After `list-sections`, fetch ALL sections relevant to the task — especially check `use_cases`.

### 3. svelte-autofixer
Analyzes Svelte code for issues and suggestions.
You MUST run this on every `.svelte` file before delivering it. Keep calling until no issues remain.

### 4. playground-link
Generates a Svelte Playground link.
Only call after user confirms they want one. NEVER call if code was written to project files.

## SPA-Specific Notes

- This is a **static SPA**: `ssr = false`, `prerender = true` — no `+page.server.ts` or server-only code
- Auth is **client-side**: `authStore` (`src/lib/stores/auth.svelte.ts`) holds the access token in memory; refresh token lives in an httpOnly cookie
- Protected pages go inside `src/routes/(protected)/` — the auth guard runs automatically via `+layout.ts`
- API calls go directly to `PUBLIC_API_URL` via the typed `client` (`src/lib/api/client.ts`) — the auth header is injected automatically by middleware
- New features belong in `src/lib/features/<name>/` with `api.ts`, `queries.ts`, `schema.ts`, `components/`
- Never add `console.log` — use toast notifications for user feedback
