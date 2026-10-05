import devtoolsJson from 'vite-plugin-devtools-json';
import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Backend dev port is 9010 (9000 belongs to another project). Same-origin via proxy keeps the
// session cookie first-party, like the production reverse proxy.
const API_TARGET = process.env.KEYCHECK_API_TARGET ?? 'http://localhost:9010';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit(), devtoolsJson()],
	server: {
		port: 5173,
		proxy: { '/api': { target: API_TARGET, changeOrigin: false } }
	},
	preview: {
		proxy: { '/api': { target: API_TARGET, changeOrigin: false } }
	}
});
