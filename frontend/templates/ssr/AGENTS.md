# Agent Instructions — SSR Template

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

## SSR-Specific Notes

- **Full-Stack & Database**: SQLite via `better-sqlite3` + `drizzle-orm` in `src/lib/server/db/`.
- **Database CLI**: `pnpm db:push` pushes schema changes to `sqlite.db`; `pnpm db:studio` inspects data.
- **Auth**: Supports server-side cookie sessions (`session_id`) and FastAPI JWT proxying (`access_token` / `refresh_token`).
- Protected pages go inside `src/routes/(protected)/` — the auth guard runs automatically via `hooks.server.ts`.
- Use `event.locals.user` / `event.locals.session` for session details; `event.locals.fastapiClient` for FastAPI calls.
- Logger: `import { logger } from '$lib/logger'` — use instead of `console.log`.
