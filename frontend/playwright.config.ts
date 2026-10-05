/// <reference types="node" />
import { defineConfig, devices } from '@playwright/test';

// e2e runs against the production build in MOCK mode (`vite build --mode test` reads .env.test,
// PUBLIC_USE_MOCK=1), so no backend is needed. `*.unit.ts` files test pure modules without a browser.
const PORT = 4173;

export default defineConfig({
	testDir: './e2e',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: process.env.CI ? 1 : 2,
	reporter: [['list'], ['html', { open: 'never' }]],
	use: {
		baseURL: `http://localhost:${PORT}`,
		trace: 'retain-on-failure',
		locale: 'th-TH',
		launchOptions: {
			args: [
				'--no-sandbox',
				'--disable-setuid-sandbox',
				'--use-fake-device-for-media-stream',
				'--use-fake-ui-for-media-stream'
			]
		}
	},
	projects: [
		{ name: 'unit', testMatch: /.*\.unit\.ts$/ },
		{ name: 'desktop', testMatch: /.*\.test\.ts$/, use: { ...devices['Desktop Chrome'] } },
		{ name: 'mobile', testMatch: /.*\.test\.ts$/, use: { ...devices['Pixel 7'] } }
	],
	webServer: {
		command: `pnpm preview --port ${PORT} --strictPort`,
		url: `http://localhost:${PORT}`,
		reuseExistingServer: !process.env.CI,
		timeout: 60_000
	}
});
