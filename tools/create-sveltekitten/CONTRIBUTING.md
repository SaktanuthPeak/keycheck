# Contributing to create-sveltekitten

## Project structure

```
src/
  index.ts          — CLI entry point: command routing + scaffold logic
  patch.ts          — `patch` command: reads .sveltekitten.json, runs codemods
  codemods/
    index.ts        — codemod registry and runner
templates/
  ssr/              — SSR template files
  spa/              — SPA template files
```

## Version tracking

Every generated project contains `.sveltekitten.json`:

```json
{
  "version": "0.1.0",
  "template": "ssr"
}
```

This file is the source of truth for which template version a project was created from. The `patch` command uses it to determine which codemods to run.

**Rule:** `package.json` version in this repo == the template version written into `.sveltekitten.json`.

## When to bump the version

| Change type | Bump |
|---|---|
| Bug fix or security fix in a template file | `patch` (0.1.0 → 0.1.1) |
| New file or feature added to template | `minor` (0.1.0 → 0.2.0) |
| Breaking change in template structure | `major` (0.1.0 → 2.0.0) |

Changes to this CLI's own source code (not template files) do not require a version bump unless they affect `patch` behavior.

## How to ship a template fix

### 1. Fix the template

Edit the file under `templates/ssr/` or `templates/spa/`.

### 2. Write a codemod

Open `src/codemods/index.ts` and add an entry to the `codemods` array **at the end**:

```ts
{
  from: '0.1.0',  // current published version
  to: '0.1.1',    // version you are about to publish
  transforms: [
    {
      file: 'src/lib/auth.ts',  // path relative to the user's project root
      transform: (content) =>
        content.replaceAll(
          `cookies.set('refreshToken'`,
          `cookies.set('refresh_token'`
        ),
    },
  ],
},
```

Rules for writing a codemod:
- `from` must be the **current latest published version** (what existing projects have in `.sveltekitten.json`)
- `to` must be the **new version** you are about to publish
- `transform` must be a pure function — same input always produces same output
- If a file might not exist in all projects, the runner skips missing files automatically
- Add one entry per bug fix — do not batch multiple unrelated fixes into one `from/to` pair

### 3. Bump the version

```bash
npm version patch   # or minor / major
```

This updates `package.json`. The scaffold and the `patch` command both read this version at runtime.

### 4. Build and publish

```bash
pnpm build
npm publish
```

## Testing a codemod locally

```bash
# 1. Build
pnpm build

# 2. Create a fake project with the old version
mkdir /tmp/test-project
echo '{"version":"0.1.0","template":"ssr"}' > /tmp/test-project/.sveltekitten.json
cp templates/ssr/src/lib/auth.ts /tmp/test-project/src/lib/auth.ts  # or just create a fixture

# 3. Run patch
(cd /tmp/test-project && node /path/to/dist/index.js patch)
```

## Codemods array order

The array in `src/codemods/index.ts` must be in **ascending version order**. The runner applies all codemods whose `to` version is greater than the project's current version and less than or equal to the latest version. This means a project at `0.1.0` will automatically chain through `0.1.1 → 0.1.2 → 0.2.0` in one `patch` run.
