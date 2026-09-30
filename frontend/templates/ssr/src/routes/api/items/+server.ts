import { json, type RequestHandler } from '@sveltejs/kit';
import {
	addItem,
	deleteItemForUser,
	ItemForbiddenError,
	ItemNotFoundError,
	listItems,
	toggleItemCompletion
} from '$lib/features/items/service';
import { createItemSchema } from '$lib/features/items/schema';

export const GET: RequestHandler = async ({ locals }) => {
	const items = await listItems(locals.user?.id);
	return json(items);
};

export const POST: RequestHandler = async ({ request, locals }) => {
	try {
		const body = await request.json();
		const result = createItemSchema.safeParse(body);
		if (!result.success) {
			return json({ error: result.error.issues[0]?.message ?? 'Invalid input' }, { status: 400 });
		}
		const created = await addItem(result.data, locals.user?.id);
		return json(created, { status: 201 });
	} catch {
		return json({ error: 'Failed to create item' }, { status: 500 });
	}
};

export const PATCH: RequestHandler = async ({ request, locals }) => {
	try {
		const body = await request.json();
		const { id, completed } = body;
		if (typeof id !== 'string' || typeof completed !== 'boolean') {
			return json({ error: 'Invalid payload' }, { status: 400 });
		}
		const updated = await toggleItemCompletion(id, completed, locals.user?.id);
		return json(updated);
	} catch (err) {
		if (err instanceof ItemNotFoundError) return json({ error: 'Item not found' }, { status: 404 });
		if (err instanceof ItemForbiddenError) return json({ error: 'Forbidden' }, { status: 403 });
		return json({ error: 'Failed to update item' }, { status: 500 });
	}
};

export const DELETE: RequestHandler = async ({ request, url, locals }) => {
	try {
		const id = url.searchParams.get('id') || (await request.json().catch(() => ({}))).id;
		if (!id || typeof id !== 'string') {
			return json({ error: 'Item ID is required' }, { status: 400 });
		}
		await deleteItemForUser(id, locals.user?.id);
		return json({ success: true });
	} catch (err) {
		if (err instanceof ItemNotFoundError) return json({ error: 'Item not found' }, { status: 404 });
		if (err instanceof ItemForbiddenError) return json({ error: 'Forbidden' }, { status: 403 });
		return json({ error: 'Failed to delete item' }, { status: 500 });
	}
};
