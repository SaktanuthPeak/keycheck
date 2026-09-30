import type { Cookies } from '@sveltejs/kit';
import jwt from 'jsonwebtoken';

function createCookieOptions(overrides: { maxAge?: number } = {}) {
	return {
		path: '/',
		httpOnly: true,
		sameSite: 'lax' as const,
		secure: process.env.NODE_ENV === 'production',
		...overrides
	};
}

export function clearCookieTokens(cookies: Cookies) {
	cookies.delete('access_token', createCookieOptions({ maxAge: 0 }));
	cookies.delete('refresh_token', createCookieOptions({ maxAge: 0 }));
}

export function isProtectedRoute(path: string | null): boolean {
	if (!path) return false;
	return path.split('/').includes('(protected)');
}

export function isTokenExpired(token?: string, bufferTime = 300): boolean {
	if (!token) return true;
	const { exp } = (jwt.decode(token) as { exp?: number }) || {};
	return !exp || Date.now() / 1000 >= exp - bufferTime;
}

export function setAuthTokens(cookies: Cookies, accessToken: string, refreshToken?: string | null) {
	cookies.set('access_token', accessToken, createCookieOptions({ maxAge: 60 * 10 }));
	if (refreshToken) {
		cookies.set('refresh_token', refreshToken, createCookieOptions({ maxAge: 60 * 60 * 24 * 7 }));
	}
}
