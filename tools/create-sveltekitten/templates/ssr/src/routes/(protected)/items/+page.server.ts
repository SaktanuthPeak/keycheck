import type { PageServerLoad } from './$types';
import { getItems } from '$lib/features/items/server';

export const load: PageServerLoad = async ({ locals }) => {
	const dbItems = await getItems(locals.user?.id);
	const items = dbItems.map((item) => ({
		id: item.id,
		title: item.title,
		description: item.description ?? undefined,
		completed: Boolean(item.completed),
		createdAt: item.createdAt instanceof Date ? item.createdAt.toISOString() : new Date(item.createdAt).toISOString()
	}));
	return { items };
};
