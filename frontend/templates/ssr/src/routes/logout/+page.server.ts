import { redirect } from '@sveltejs/kit';
import { clearCookieTokens } from '$lib/utils/auth';
import { deleteSessionCookie, invalidateSession } from '$lib/server/auth/session';
import type { Actions } from './$types';

export const actions: Actions = {
	default: async ({ cookies }) => {
		const sessionId = cookies.get('session_id');
		if (sessionId) {
			await invalidateSession(sessionId);
			deleteSessionCookie(cookies);
		}
		clearCookieTokens(cookies);
		throw redirect(303, '/login');
	}
};
