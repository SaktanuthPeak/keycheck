import type { Codemod } from './index.js';

const MOCK_JWT =
	'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6OTk5OTk5OTk5OX0.fake';

const ssrPlaywrightConfig = `import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
\ttestDir: './e2e',
\tfullyParallel: true,
\tforbidOnly: !!process.env.CI,
\tretries: process.env.CI ? 2 : 0,
\tworkers: process.env.CI ? 1 : undefined,
\treporter: 'html',
\tuse: {
\t\tbaseURL: 'http://localhost:3000',
\t\ttrace: 'on-first-retry',
\t\tlaunchOptions: {
\t\t\targs: ['--no-sandbox', '--disable-setuid-sandbox'],
\t\t},
\t},
\tprojects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
\twebServer: [
\t\t{
\t\t\tcommand: 'node e2e/mock-api.js',
\t\t\turl: 'http://localhost:9001',
\t\t\treuseExistingServer: !process.env.CI,
\t\t},
\t\t{
\t\t\tcommand: 'pnpm build && node build',
\t\t\turl: 'http://localhost:3000',
\t\t\treuseExistingServer: !process.env.CI,
\t\t\tenv: { BACKEND_API_URL: 'http://localhost:9001' },
\t\t},
\t],
});
`;

const spaPlaywrightConfig = `import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
\ttestDir: './e2e',
\tfullyParallel: true,
\tforbidOnly: !!process.env.CI,
\tretries: process.env.CI ? 2 : 0,
\tworkers: process.env.CI ? 1 : undefined,
\treporter: 'html',
\tuse: {
\t\tbaseURL: 'http://localhost:4173',
\t\ttrace: 'on-first-retry',
\t\tlaunchOptions: {
\t\t\targs: ['--no-sandbox', '--disable-setuid-sandbox'],
\t\t},
\t},
\tprojects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
\twebServer: {
\t\tcommand: 'pnpm build && pnpm preview',
\t\turl: 'http://localhost:4173',
\t\treuseExistingServer: !process.env.CI,
\t},
});
`;

const ssrMockApi = `import { createServer } from 'node:http';

// Valid JWTs with exp: 9999999999 (year 2286) — jwt.decode() parses without verification
const MOCK_ACCESS_TOKEN = '${MOCK_JWT}';
const MOCK_REFRESH_TOKEN = '${MOCK_JWT}';

const VALID = { username: 'admin', password: 'secret' };

const server = createServer(async (req, res) => {
\tconst chunks = [];
\tfor await (const chunk of req) chunks.push(chunk);
\tconst body = JSON.parse(Buffer.concat(chunks).toString() || '{}');

\tres.setHeader('Content-Type', 'application/json');

\tif (req.method === 'POST' && req.url === '/v1/auth/login') {
\t\tif (body.username === VALID.username && body.password === VALID.password) {
\t\t\tres.writeHead(200);
\t\t\tres.end(JSON.stringify({ access_token: MOCK_ACCESS_TOKEN, refresh_token: MOCK_REFRESH_TOKEN, token_type: 'bearer' }));
\t\t} else {
\t\t\tres.writeHead(401);
\t\t\tres.end(JSON.stringify({ detail: 'Invalid credentials' }));
\t\t}
\t\treturn;
\t}

\tif (req.method === 'POST' && req.url === '/v1/auth/refresh') {
\t\tres.writeHead(200);
\t\tres.end(JSON.stringify({ access_token: MOCK_ACCESS_TOKEN, refresh_token: MOCK_REFRESH_TOKEN, token_type: 'bearer' }));
\t\treturn;
\t}

\tres.writeHead(404);
\tres.end(JSON.stringify({ detail: 'Not found' }));
});

server.listen(9001, () => console.log('Mock API running on http://localhost:9001'));
`;

const ssrLoginTest = `import { test, expect } from '@playwright/test';

const VALID = { username: 'admin', password: 'secret' };
const INVALID = { username: 'wrong', password: 'wrong' };

test.describe('Login', () => {
\ttest('shows login form', async ({ page }) => {
\t\tawait page.goto('/login');
\t\tawait expect(page.getByLabel('Username')).toBeVisible();
\t\tawait expect(page.getByLabel('Password')).toBeVisible();
\t\tawait expect(page.getByRole('button', { name: 'Login' })).toBeVisible();
\t});

\ttest('redirects to /home on valid credentials', async ({ page }) => {
\t\tawait page.goto('/login');
\t\tawait page.getByLabel('Username').fill(VALID.username);
\t\tawait page.getByLabel('Password').fill(VALID.password);
\t\tawait page.getByRole('button', { name: 'Login' }).click();
\t\tawait expect(page).toHaveURL('/home');
\t});

\ttest('shows error toast on invalid credentials', async ({ page }) => {
\t\tawait page.goto('/login');
\t\tawait page.getByLabel('Username').fill(INVALID.username);
\t\tawait page.getByLabel('Password').fill(INVALID.password);
\t\tawait page.getByRole('button', { name: 'Login' }).click();
\t\tawait expect(page.getByText('Login Failed')).toBeVisible();
\t});
});
`;

const spaLoginTest = `import { test, expect } from '@playwright/test';

const MOCK_TOKENS = {
\taccess_token: '${MOCK_JWT}',
\trefresh_token: '${MOCK_JWT}',
\ttoken_type: 'bearer',
};

const MOCK_USER = {
\tusername: 'admin',
\tname: 'Admin',
\tid: 1,
\trole: 'admin',
\tis_active: true,
\temail: 'admin@test.com',
\tlast_login_date: null,
\tcreated_at: new Date().toISOString(),
};

test.describe('Login', () => {
\ttest('shows login form', async ({ page }) => {
\t\tawait page.goto('/login');
\t\tawait expect(page.getByLabel('Username')).toBeVisible();
\t\tawait expect(page.getByLabel('Password')).toBeVisible();
\t\tawait expect(page.getByRole('button', { name: 'Login' })).toBeVisible();
\t});

\ttest('redirects to /home on valid credentials', async ({ page }) => {
\t\tawait page.route('**/v1/auth/login', (route) =>
\t\t\troute.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_TOKENS) })
\t\t);
\t\tawait page.route('**/v1/users/me', (route) =>
\t\t\troute.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_USER) })
\t\t);

\t\tawait page.goto('/login');
\t\tawait page.getByLabel('Username').fill('admin');
\t\tawait page.getByLabel('Password').fill('secret');
\t\tawait page.getByRole('button', { name: 'Login' }).click();
\t\tawait expect(page).toHaveURL('/home');
\t});

\ttest('shows error toast on invalid credentials', async ({ page }) => {
\t\tawait page.route('**/v1/auth/login', (route) =>
\t\t\troute.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ detail: 'Invalid credentials' }) })
\t\t);

\t\tawait page.goto('/login');
\t\tawait page.getByLabel('Username').fill('wrong');
\t\tawait page.getByLabel('Password').fill('wrong');
\t\tawait page.getByRole('button', { name: 'Login' }).click();
\t\tawait expect(page.getByText('Invalid credentials')).toBeVisible();
\t});
});
`;

const gitignoreAdditions = `
# Playwright
test-results/
playwright-report/
blob-report/
.playwright/`;

function addPlaywrightToPackageJson(content: string): string {
	const pkg = JSON.parse(content);
	pkg.scripts['test:e2e'] = 'playwright test';
	pkg.devDependencies = {
		'@playwright/test': '^1.52.0',
		...pkg.devDependencies,
	};
	return JSON.stringify(pkg, null, '\t');
}

const codemod: Codemod = {
	from: '0.2.1',
	to: '0.2.2',
	transforms: [
		// SSR-specific files
		{
			file: 'playwright.config.ts',
			create: true,
			template: 'ssr',
			transform: () => ssrPlaywrightConfig,
		},
		{
			file: 'e2e/mock-api.js',
			create: true,
			template: 'ssr',
			transform: () => ssrMockApi,
		},
		{
			file: 'e2e/login.test.ts',
			create: true,
			template: 'ssr',
			transform: () => ssrLoginTest,
		},
		// SPA-specific files
		{
			file: 'playwright.config.ts',
			create: true,
			template: 'spa',
			transform: () => spaPlaywrightConfig,
		},
		{
			file: 'e2e/login.test.ts',
			create: true,
			template: 'spa',
			transform: () => spaLoginTest,
		},
		// Both templates
		{
			file: 'package.json',
			transform: addPlaywrightToPackageJson,
		},
		{
			file: '.gitignore',
			transform: (content) =>
				content.includes('# Playwright') ? content : content + gitignoreAdditions + '\n',
		},
	],
};

export default codemod;
