import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	// SPA: dynamic routes such as /inspections/[id] are served by the fallback page
	// (the reverse proxy must rewrite unknown paths to /200.html).
	kit: { adapter: adapter({ fallback: '200.html' }) }
};

export default config;
