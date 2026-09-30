const OLD_SERVER_IMPORTS = `import { db } from '$lib/server/db';
import { items, type DbItem } from '$lib/server/db/schema';
import { eq, desc } from 'drizzle-orm';
import type { CreateItemInput } from './schema';`;
const NEW_SERVER_IMPORTS = `import { db } from '$lib/server/db';
import { items, type DbItem } from '$lib/server/db/schema';
import { eq, desc } from 'drizzle-orm';
import type { CreateItemInput } from './schema';

export type { DbItem };`;
const OLD_INSERT_ITEM_SIG = `export async function insertItem(input: CreateItemInput, userId?: string): Promise<DbItem> {`;
const NEW_GET_ITEM_BY_ID = `export async function getItemById(id: string): Promise<DbItem | undefined> {
	return db.select().from(items).where(eq(items.id, id)).get();
}

export async function insertItem(input: CreateItemInput, userId?: string): Promise<DbItem> {`;
const SERVICE_FILE = `import {
	getItemById,
	getItems,
	insertItem,
	removeItem,
	updateItemCompletion,
	type DbItem
} from './server';
import type { CreateItemInput } from './schema';

export class ItemNotFoundError extends Error {}
export class ItemForbiddenError extends Error {}

async function assertOwnedByUser(id: string, userId: string | undefined): Promise<DbItem> {
	const existing = await getItemById(id);
	if (!existing) throw new ItemNotFoundError();
	if (existing.userId && existing.userId !== userId) throw new ItemForbiddenError();
	return existing;
}

export async function listItems(userId?: string): Promise<DbItem[]> {
	return getItems(userId);
}

export async function addItem(input: CreateItemInput, userId?: string): Promise<DbItem> {
	return insertItem(input, userId);
}

export async function toggleItemCompletion(
	id: string,
	completed: boolean,
	userId?: string
): Promise<DbItem> {
	await assertOwnedByUser(id, userId);
	const updated = await updateItemCompletion(id, completed);
	if (!updated) throw new ItemNotFoundError();
	return updated;
}

export async function deleteItemForUser(id: string, userId?: string): Promise<void> {
	await assertOwnedByUser(id, userId);
	await removeItem(id);
}
`;
const NEW_SERVER_ROUTE = `import { json, type RequestHandler } from '@sveltejs/kit';
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
`;
const codemod = {
    from: '0.3.1',
    to: '0.3.2',
    transforms: [
        {
            file: 'src/lib/features/items/server.ts',
            template: 'ssr',
            transform: (content) => {
                let next = content;
                if (!next.includes('export type { DbItem };') && next.includes(OLD_SERVER_IMPORTS)) {
                    next = next.replace(OLD_SERVER_IMPORTS, NEW_SERVER_IMPORTS);
                }
                if (!next.includes('export async function getItemById') && next.includes(OLD_INSERT_ITEM_SIG)) {
                    next = next.replace(OLD_INSERT_ITEM_SIG, NEW_GET_ITEM_BY_ID);
                }
                return next;
            }
        },
        {
            // New use-case layer between the route and the repository: this is where
            // per-item ownership checks live, since the repository never verified
            // that a toggled/deleted item's userId matched the requesting user.
            file: 'src/lib/features/items/service.ts',
            template: 'ssr',
            create: true,
            transform: () => SERVICE_FILE
        },
        {
            file: 'src/routes/api/items/+server.ts',
            template: 'ssr',
            transform: (content) => {
                if (!content.includes("from '$lib/features/items/server'"))
                    return content;
                return NEW_SERVER_ROUTE;
            }
        }
    ]
};
export default codemod;
