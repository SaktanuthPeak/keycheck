import { db } from '$lib/server/db';
import { sessions, users, type User, type Session } from '$lib/server/db/schema';
import { eq } from 'drizzle-orm';
import type { Cookies } from '@sveltejs/kit';
import { randomBytes } from 'node:crypto';

export const SESSION_COOKIE_NAME = 'session_id';
const SESSION_DURATION_MS = 1000 * 60 * 60 * 24 * 7; // 7 days

export function generateSessionToken(): string {
	return randomBytes(32).toString('hex');
}

export async function createSession(token: string, userId: string): Promise<Session> {
	const expiresAt = new Date(Date.now() + SESSION_DURATION_MS);
	const [session] = await db
		.insert(sessions)
		.values({
			id: token,
			userId,
			expiresAt
		})
		.returning();
	return session;
}

export async function validateSessionToken(
	token: string
): Promise<{ session: Session; user: User } | { session: null; user: null }> {
	try {
		const result = await db
			.select({
				session: sessions,
				user: {
					id: users.id,
					username: users.username,
					createdAt: users.createdAt
				}
			})
			.from(sessions)
			.innerJoin(users, eq(sessions.userId, users.id))
			.where(eq(sessions.id, token))
			.get();

		if (!result) {
			return { session: null, user: null };
		}

		const { session, user } = result;

		// Check expiration
		if (Date.now() >= session.expiresAt.getTime()) {
			await db.delete(sessions).where(eq(sessions.id, session.id));
			return { session: null, user: null };
		}

		// Extend session if within 3 days of expiring
		if (Date.now() >= session.expiresAt.getTime() - 1000 * 60 * 60 * 24 * 3) {
			session.expiresAt = new Date(Date.now() + SESSION_DURATION_MS);
			await db
				.update(sessions)
				.set({ expiresAt: session.expiresAt })
				.where(eq(sessions.id, session.id));
		}

		return { session, user: user as User };
	} catch {
		return { session: null, user: null };
	}
}

export async function invalidateSession(sessionId: string): Promise<void> {
	try {
		await db.delete(sessions).where(eq(sessions.id, sessionId));
	} catch {
		// ignore
	}
}

export function setSessionCookie(cookies: Cookies, token: string, expiresAt: Date) {
	cookies.set(SESSION_COOKIE_NAME, token, {
		httpOnly: true,
		path: '/',
		sameSite: 'lax',
		secure: process.env.NODE_ENV === 'production',
		expires: expiresAt
	});
}

export function deleteSessionCookie(cookies: Cookies) {
	cookies.delete(SESSION_COOKIE_NAME, {
		httpOnly: true,
		path: '/',
		sameSite: 'lax',
		secure: process.env.NODE_ENV === 'production'
	});
}
