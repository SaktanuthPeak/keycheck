import type { Codemod } from './index.js';

function updatePackageJson(content: string, isSsr: boolean): string {
	const pkg = JSON.parse(content);
	if (pkg.dependencies) {
		if (pkg.dependencies['@tanstack/svelte-query']) {
			pkg.dependencies['@tanstack/svelte-query'] = '^6.1.38';
		}
		if (pkg.dependencies['@tanstack/svelte-query-devtools']) {
			pkg.dependencies['@tanstack/svelte-query-devtools'] = '^6.1.38';
		}
	}
	if (pkg.devDependencies) {
		const devUpdates: Record<string, string> = {
			'@internationalized/date': '^3.12.3',
			'@lucide/svelte': '^1.31.0',
			'@playwright/test': '^1.62.1',
			'@tailwindcss/vite': '^4.3.3',
			globals: '^17.11.0',
			'prettier-plugin-tailwindcss': '^0.8.1',
			'svelte-check': '^4.7.6',
			'tailwind-variants': '^3.3.1',
			tailwindcss: '^4.3.3',
			'vite-plugin-devtools-json': '^1.1.0',
		};
		if (isSsr) {
			devUpdates['@sveltejs/adapter-node'] = '^5.5.7';
			devUpdates['@types/node'] = '^26.2.0';
		}
		for (const [name, ver] of Object.entries(devUpdates)) {
			if (pkg.devDependencies[name]) {
				pkg.devDependencies[name] = ver;
			}
		}
	}
	return JSON.stringify(pkg, null, '\t') + '\n';
}

function updatePrettierIgnore(content: string): string {
	if (!content.includes('.agents/')) {
		return content.trimEnd() + '\n.agents/\n';
	}
	return content;
}

const codemod: Codemod = {
	from: '0.2.4',
	to: '0.2.5',
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
		{
			file: '.prettierignore',
			transform: updatePrettierIgnore,
		},
	],
};

export default codemod;
