import { clearCookieTokens, isProtectedRoute, isTokenExpired } from '$lib/utils/auth';
import { validateSessionToken, setSessionCookie, deleteSessionCookie } from '$lib/server/auth/session';
import type { Handle } from '@sveltejs/kit';

export const handleAuthGuard: Handle = async ({ event, resolve }) => {
	const { cookies, route } = event;

	// 1. Check SQLite session token first
	const sessionId = cookies.get('session_id');
	if (sessionId) {
		const { session, user } = await validateSessionToken(sessionId);
		if (session && user) {
			event.locals.session = session;
			event.locals.user = user;
			setSessionCookie(cookies, sessionId, session.expiresAt);
		} else {
			deleteSessionCookie(cookies);
			event.locals.session = null;
			event.locals.user = null;
		}
	} else {
		event.locals.session = null;
		event.locals.user = null;
	}

	// 2. Check FastAPI refresh token
	const refreshToken = cookies.get('refresh_token');
	if (refreshToken && isTokenExpired(refreshToken)) {
		clearCookieTokens(cookies);
	}

	// 3. Route Guard for (protected) route group
	if (isProtectedRoute(route.id)) {
		const isAuthenticated = Boolean(
			event.locals.user || (refreshToken && !isTokenExpired(refreshToken))
		);

		if (!isAuthenticated) {
			return new Response(null, {
				status: 303,
				headers: { location: '/login' }
			});
		}
	}

	const response = await resolve(event);
	return response;
};
