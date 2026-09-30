import { authStore } from '$lib/stores/auth.svelte';
import type { components } from './openapi';
import client from './client';

// Singleton state for token refresh coordination
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;
let refreshSubscribers: Array<(token: string | null) => void> = [];

/**
 * Subscribe to token refresh completion
 */
function subscribeToRefresh(callback: (token: string | null) => void) {
	refreshSubscribers.push(callback);
}

/**
 * Notify all subscribers that refresh is complete
 */
function notifyRefreshComplete(token: string | null) {
	refreshSubscribers.forEach((callback) => callback(token));
	refreshSubscribers = [];
}

/**
 * Check if currently refreshing token
 */
export function isCurrentlyRefreshing(): boolean {
	return isRefreshing;
}

/**
 * Wait for ongoing token refresh to complete
 */
export function waitForRefresh(): Promise<string | null> {
	return new Promise((resolve) => {
		subscribeToRefresh(resolve);
	});
}

/**
 * Refresh access token using refresh token
 * ไม่ควร redirect ใน utility function - ให้ caller (guard) จัดการแทน
 */
export async function refreshAccessToken(): Promise<boolean> {
	// ถ้ากำลัง refresh อยู่แล้ว ให้รอ promise เดิม
	if (isRefreshing && refreshPromise) {
		return refreshPromise;
	}

	isRefreshing = true;
	refreshPromise = (async () => {
		try {
			// Use httpOnly cookie - browser sends cookie automatically
			const { data, error, response } = await client.GET('/v1/auth/refresh_token', {
				credentials: 'include'
			});

			if (!response.ok) {
				// ไม่ redirect ที่นี่ ให้ caller จัดการ
				notifyRefreshComplete(null);
				return false;
			}

			if (!data) {
				notifyRefreshComplete(null);
				return false;
			}

			// API คืน GetAccessTokenResponse { access_token, token_type }
			type GetAccessTokenResponse = components['schemas']['GetAccessTokenResponse'];

			// Update แค่ access token (ไม่มี refresh_token ใหม่)
			authStore.updateAccessToken(data.access_token, data.token_type);

			// Notify all waiting requests
			notifyRefreshComplete(data.access_token);
			return true;
		} catch (error) {
			notifyRefreshComplete(null);

			// ไม่ redirect ที่นี่ ให้ caller จัดการ
			return false;
		} finally {
			isRefreshing = false;
			refreshPromise = null;
		}
	})();

	return refreshPromise;
}

/**
 * Wrapper function to automatically handle 401 errors and retry with refreshed token
 */
export async function fetchWithAuth<T>(
	fetcher: () => Promise<{ data?: T; error?: unknown }>,
	retry = true
): Promise<{ data?: T; error?: unknown }> {
	const result = await fetcher();

	// ถ้าได้ 401 และยังสามารถ retry ได้
	if (
		result.error &&
		typeof result.error === 'object' &&
		'status' in result.error &&
		result.error.status === 401 &&
		retry
	) {
		const refreshed = await refreshAccessToken();
		if (refreshed) {
			// ลองเรียก API อีกครั้งหลัง refresh token
			return fetchWithAuth(fetcher, false);
		}
	}

	return result;
}

/**
 * Check and refresh token if needed before making requests
 * bufferTime = 120 seconds (2 minutes)
 */
export async function ensureValidToken(): Promise<boolean> {
	// รอให้ auth store โหลดข้อมูลจาก storage ก่อน
	await authStore.ensureInitialized();

	if (!authStore.isAuthenticated) {
		return false;
	}

	// ถ้า access token หมดอายุแล้ว หรือใกล้จะหมดอายุ (bufferTime = 120 seconds = 2 minutes) ให้ refresh
	const expiringSoon = authStore.isTokenExpiringSoon(120); // 120 seconds = 2 minutes

	if (expiringSoon) {
		const result = await refreshAccessToken();
		return result;
	}

	return true;
}
