# AGENTS.md — create-sveltekitten

This is a CLI scaffolding tool (`pnpx create-sveltekitten`). It generates SvelteKit projects from templates and can patch existing projects via a codemod system. See `CONTRIBUTING.md` for the full narrative walkthrough of shipping a template fix.

## Commands

```bash
pnpm build    # compile src/ → dist/ (tsc) — always run after editing src/
pnpm dev      # run CLI directly via tsx (for local testing)
```

Run the CLI locally:
```bash
node dist/index.js            # scaffold (interactive)
node dist/index.js patch      # patch an existing project
```

The `dist/` directory is committed — always rebuild before committing.

## Repository layout

```
src/
  index.ts          — entry point: routes commands, contains scaffold logic
  patch.ts          — patch command implementation
  codemods/
    index.ts        — codemod registry + runner
templates/
  ssr/              — SSR template
  spa/              — SPA template
dist/               — compiled output (committed, enables pnpx github: usage)
```

## Template version system

Every scaffolded project receives a `.sveltekitten.json`:
```json
{ "version": "0.1.0", "template": "ssr" }
```

The version comes from `package.json` at scaffold time. The `patch` command uses it to select applicable codemods.

## Feature architecture convention (inside templates)

Template features under `src/lib/features/<name>/` follow a layered pattern — `src/lib/features/items/` in each template is the canonical example, see `templates/ssr/agent-role.md` / `templates/spa/agent-role.md` for the full breakdown:

- `schema.ts` (Zod) → `port.ts` (interface) → `api.ts` (implements the port) → `queries.ts` (TanStack Query hooks, depend on the port via an optional injected parameter, not on `api.ts` directly)
- SSR full-stack features additionally split `server.ts` (Drizzle repository, no business rules) from `service.ts` (use-case layer with authorization — e.g. ownership checks). Route handlers (`src/routes/api/<feature>/+server.ts`) call `service.ts`, never `server.ts` directly.

When this pattern changes, update it in three places together: the template files themselves, `templates/ssr/agent-role.md` / `templates/spa/agent-role.md`, and this section.

## Fixing a bug in a template file

Never change a template file without a matching codemod entry — existing projects cannot receive the fix otherwise.

You must always do all these steps — never skip any:

1. **Edit** the file under `templates/ssr/` or `templates/spa/`
2. **Add a codemod** — an entry in the `codemods` array in `src/codemods/index.ts`, **at the end**, so existing projects can receive the fix
3. **Bump the version** in `package.json` (`npm version patch` / `minor` / `major`)
4. `pnpm build && npm publish`

### Codemod entry shape

```ts
{
  from: '<current published version>',
  to: '<new version>',
  transforms: [
    {
      file: 'relative/path/from/project/root.ts',
      transform: (content: string) => content.replaceAll('old', 'new'),
    },
  ],
}
```

### Codemod rules

- Entries in the `codemods` array must be in ascending version order
- `from` = current published version, `to` = new version being released
- `transform` must be a pure function (no side effects, no I/O)
- Missing files are skipped automatically by the runner
- Add one entry per bug fix — do not batch multiple unrelated fixes into one `from`/`to` pair

**If two codemods in the array touch the same file** (e.g. one adds a function, a later one changes how the route calls it), `patch.ts` chains them correctly within a single run — each transform sees the previous transform's output for that file, not stale on-disk content. This only works because transforms stay pure and guarded (check before replacing); don't rely on a transform re-reading the file from disk mid-run.

## When editing CLI source only (not templates)

No version bump needed unless the change affects `patch` behavior.

## Testing

```bash
pnpm build
node dist/index.js patch   # run inside a project with .sveltekitten.json
```

To test a codemod without an actual project, create a temp directory with a `.sveltekitten.json` and relevant fixture files, then run `node dist/index.js patch` from that directory.

## Do not

- Add new commands by modifying `main()` — add a new branch in the `command` switch at the bottom of `index.ts`
- Write codemods that assume file structure beyond what the template generates
- Bump the version without adding a codemod when a template file changes
- Edit `dist/` files by hand — always go through `src/` + `pnpm build`
- Add codemods out of version order
- Write transforms with side effects or I/O

---
`CLAUDE.md` in this repo is a symlink to this file, kept so tools that specifically look for that filename (e.g. Claude Code) still resolve to the same content. Edit this file, not that one.
