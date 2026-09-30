import jwt from 'jsonwebtoken';
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ cookies, locals }) => {
	if (locals.user) {
		return { user: { username: locals.user.username } };
	}
	const accessToken = cookies.get('access_token');
	const payload = accessToken
		? (jwt.decode(accessToken) as { sub?: string } | null)
		: null;
	return { user: { username: payload?.sub ?? 'User' } };
};
