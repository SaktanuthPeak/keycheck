import { test, expect } from '@playwright/test';

const VALID = { username: 'admin', password: 'secret' };
const INVALID = { username: 'wrong', password: 'wrongpass' };

test.describe('Login', () => {
	test('shows login form', async ({ page }) => {
		await page.goto('/login');
		await expect(page.getByLabel('Username')).toBeVisible();
		await expect(page.getByLabel('Password')).toBeVisible();
		await expect(page.getByRole('button', { name: 'Login' })).toBeVisible();
	});

	test('redirects to /home on valid credentials', async ({ page }) => {
		await page.goto('/login');
		await page.getByLabel('Username').fill(VALID.username);
		await page.getByLabel('Password').fill(VALID.password);
		await page.getByRole('button', { name: 'Login' }).click();
		await expect(page).toHaveURL('/home');
	});

	test('shows error toast on invalid credentials', async ({ page }) => {
		await page.goto('/login');
		await page.getByLabel('Username').fill(INVALID.username);
		await page.getByLabel('Password').fill(INVALID.password);
		await page.getByRole('button', { name: 'Login' }).click();
		await expect(page.getByText('Login Failed', { exact: true })).toBeVisible();
	});
});
