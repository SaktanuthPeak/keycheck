# SOLID in Practice — deck

Slidev deck that walks through SOLID using the SSR template in `templates/ssr/`.
Slide content is English; speaker notes are Thai.

```bash
pnpm install --ignore-workspace   # the repo root has a pnpm-workspace.yaml
pnpm dev                          # http://localhost:3030
```

- Presenter mode (Thai notes, timer, next slide): http://localhost:3030/presenter
- Static build: `pnpm build` → `dist/`
- PDF: `pnpm export` (needs `playwright-chromium`)

Code on slides is copied verbatim from the template and tagged with its
source path. `port.ts` and `schema.ts` are imported live with `<<<`, so they
follow the template automatically; the other excerpts must be re-checked when
the template changes.
