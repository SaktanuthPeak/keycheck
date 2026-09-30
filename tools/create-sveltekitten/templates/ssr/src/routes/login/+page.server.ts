import { redirect, type Actions } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';
import { message, superValidate } from 'sveltekit-superforms';
import { zod4 } from 'sveltekit-superforms/adapters';
import { loginSchema } from '$lib/features/login/schema';
import { logger } from '$lib/logger';
import { setAuthTokens, isTokenExpired } from '$lib/utils/auth';
import { db } from '$lib/server/db';
import { users } from '$lib/server/db/schema';
import { eq } from 'drizzle-orm';
import { hashPassword, verifyPassword } from '$lib/server/auth/password';
import { createSession, generateSessionToken, setSessionCookie } from '$lib/server/auth/session';

export const load = (async ({ cookies, locals }) => {
	if (locals.user) {
		throw redirect(303, '/home');
	}
	const refreshToken = cookies.get('refresh_token');
	if (refreshToken && !isTokenExpired(refreshToken)) {
		throw redirect(303, '/home');
	}

	const form = await superValidate(zod4(loginSchema));

	return { form };
}) satisfies PageServerLoad;

export const actions: Actions = {
	default: async ({ request, locals, cookies }) => {
		const { fastapiClient } = locals;
		const form = await superValidate(request, zod4(loginSchema));

		logger.info({ formData: form.data }, 'Login form data');

		if (!form.valid) {
			return { form };
		}

		// Try FastAPI first if BACKEND_API_URL is configured and not default placeholder
		const backendUrl = process.env.BACKEND_API_URL;
		if (backendUrl && backendUrl !== 'http://localhost:9000') {
			try {
				const result = await fastapiClient.POST('/v1/auth/login', {
					body: {
						username: form.data.username,
						password: form.data.password,
						strategy: 'jwt'
					}
				});
				logger.inspect('FastAPI Login Result', result);

				if (result.data) {
					setAuthTokens(cookies, result.data.access_token, result.data.refresh_token);
					throw redirect(303, '/home');
				}
			} catch (err) {
				if ((err as any)?.status === 303) throw err;
				logger.inspect('FastAPI login failed, checking local database', err);
			}
		}

		// Local Full-Stack SQLite Authentication
		try {
			const existingUser = db
				.select()
				.from(users)
				.where(eq(users.username, form.data.username))
				.get();

			if (!existingUser) {
				// Out-of-the-box user creation for initial onboarding
				const newUserId = crypto.randomUUID();
				const passwordHash = hashPassword(form.data.password);
				db.insert(users)
					.values({
						id: newUserId,
						username: form.data.username,
						passwordHash,
						createdAt: new Date()
					})
					.run();

				const token = generateSessionToken();
				const session = await createSession(token, newUserId);
				setSessionCookie(cookies, token, session.expiresAt);
			} else {
				const valid = verifyPassword(form.data.password, existingUser.passwordHash);
				if (!valid) {
					return message(
						form,
						{
							type: 'error',
							text: 'Invalid username or password.'
						},
						{ status: 400 }
					);
				}

				const token = generateSessionToken();
				const session = await createSession(token, existingUser.id);
				setSessionCookie(cookies, token, session.expiresAt);
			}
		} catch (err) {
			logger.inspect('Local login error', err);
			return message(
				form,
				{
					type: 'error',
					text: 'An error occurred during authentication. Please try again.'
				},
				{ status: 500 }
			);
		}

		throw redirect(303, '/home');
	}
};
