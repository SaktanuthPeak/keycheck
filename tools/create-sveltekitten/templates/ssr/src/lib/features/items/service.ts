import {
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
