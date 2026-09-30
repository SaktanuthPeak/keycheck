import type { Codemod } from './index.js';

const DEP_UPDATES: Record<string, string> = {
	'@tanstack/svelte-query': '^6.3.0',
	'@tanstack/svelte-query-devtools': '^6.3.0',
};

const DEV_DEP_UPDATES: Record<string, string> = {
	'@eslint/compat': '^2.1.1',
	'@internationalized/date': '^3.12.4',
	'@lucide/svelte': '^1.48.0',
	'@playwright/test': '^1.63.0',
	'@sveltejs/kit': '^2.70.3',
	'@sveltejs/vite-plugin-svelte': '^7.3.1',
	'bits-ui': '^2.19.3',
	eslint: '^10.11.0',
	'eslint-plugin-svelte': '^3.23.0',
	globals: '^17.12.0',
	prettier: '^3.9.9',
	svelte: '^5.57.1',
	'svelte-sonner': '^1.2.1',
	'sveltekit-superforms': '^2.30.2',
	'tailwind-merge': '^3.7.0',
	'typescript-eslint': '^8.70.1',
	vite: '^8.3.1',
	zod: '^4.6.5',
};

function updatePackageJson(content: string, isSsr: boolean): string {
	const pkg = JSON.parse(content);
	if (pkg.dependencies) {
		for (const [name, ver] of Object.entries(DEP_UPDATES)) {
			if (pkg.dependencies[name]) {
				pkg.dependencies[name] = ver;
			}
		}
	}
	if (pkg.devDependencies) {
		const devUpdates = { ...DEV_DEP_UPDATES };
		if (isSsr) {
			devUpdates['@types/node'] = '^26.6.3';
		}
		for (const [name, ver] of Object.entries(devUpdates)) {
			if (pkg.devDependencies[name]) {
				pkg.devDependencies[name] = ver;
			}
		}
	}
	return JSON.stringify(pkg, null, '\t') + '\n';
}

const codemod: Codemod = {
	from: '0.3.3',
	to: '0.3.4',
	transforms: [
		{
			file: 'package.json',
			template: 'spa',
			transform: (content) => updatePackageJson(content, false),
		},
		{
			file: 'package.json',
			template: 'ssr',
			transform: (content) => updatePackageJson(content, true),
		},
	],
};

export default codemod;
