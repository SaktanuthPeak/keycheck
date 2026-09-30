import { authStore } from '$lib/stores/auth.svelte';
import { redirect } from '@sveltejs/kit';
import { browser } from '$app/environment';
import { ensureValidToken } from '$lib/api/auth-interceptor';

/**
 * Auth guard for protected routes
 * ใช้ใน load function ของ +layout.ts หรือ +page.ts
 * จะตรวจสอบ authentication และพยายาม refresh token ถ้าหมดอายุ
 * คล้ายกับ authHandler ใน SSR version (hooks.server.ts)
 *
 * @example
 * // src/routes/dashboard/+layout.ts
 * import { requireAuth } from '$lib/guards/auth';
 *
 * export const load = async () => {
 *   await requireAuth();
 *   return {};
 * };
 */
export async function requireAuth() {
	if (!browser) return;

	// รอให้ auth store โหลดจาก storage ก่อน
	authStore.ensureInitialized();

	if (!authStore.isAuthenticated) {
		throw redirect(302, '/login');
	}

	// เช็ค access token expired
	const accessTokenExpired = authStore.isTokenExpired(60); // buffer 60 seconds

	if (accessTokenExpired) {
		const refreshed = await ensureValidToken();

		if (!refreshed) {
			throw redirect(302, '/login');
		}
	}
}

/**
 * Redirect to home if already authenticated
 * ใช้สำหรับหน้า login/register เพื่อป้องกันการเข้าถึงเมื่อ login แล้ว
 *
 * @example
 * // src/routes/login/+page.ts
 * import { redirectIfAuthenticated } from '$lib/guards/auth';
 *
 * export const load = async () => {
 *   await redirectIfAuthenticated();
 *   return {};
 * };
 */
export async function redirectIfAuthenticated(redirectTo = '/') {
	if (!browser) return;

	// รอให้ auth store โหลดจาก storage ก่อน
	await authStore.ensureInitialized();

	const isAuth = authStore.isAuthenticated;
	const isExpired = authStore.isTokenExpired();

	if (isAuth && !isExpired) {
		throw redirect(302, redirectTo);
	}
}
