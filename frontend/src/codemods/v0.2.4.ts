import type { Codemod } from './index.js';

const spaGitignore = `node_modules

# Output
.output
.vercel
.netlify
.wrangler
/.svelte-kit
/build

# OS
.DS_Store
Thumbs.db

# Env
.env
.env.*
!.env.example
!.env.test

# Vite
vite.config.js.timestamp-*
vite.config.ts.timestamp-*

# Paraglide
src/lib/paraglide

# openapi generated types
src/lib/api/openapi.d.ts

# Playwright
test-results/
playwright-report/
blob-report/
.playwright/
`;

const ssrGitignore = `node_modules

# Output
.output
.vercel
.netlify
.wrangler
/.svelte-kit
/build

# OS
.DS_Store
Thumbs.db

# Env
.env
.env.*
!.env.example
!.env.test

# Vite
vite.config.js.timestamp-*
vite.config.ts.timestamp-*

# Paraglide
src/lib/paraglide

# openapi generated types
src/lib/api/paths/

# Playwright
test-results/
playwright-report/
blob-report/
.playwright/
`;

const codemod: Codemod = {
	from: '0.2.3',
	to: '0.2.4',
	transforms: [
		{
			file: '.gitignore',
			create: true,
			template: 'spa',
			transform: () => spaGitignore,
		},
		{
			file: '.gitignore',
			create: true,
			template: 'ssr',
			transform: () => ssrGitignore,
		},
	],
};

export default codemod;
