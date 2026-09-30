import type { Item, CreateItemInput } from './schema';
import type { ItemsApi } from './port';

export async function fetchItems(): Promise<Item[]> {
	const res = await fetch('/api/items');
	if (!res.ok) throw new Error('Failed to fetch items');
	const data = await res.json();
	return data.map((d: any) => ({
		...d,
		description: d.description ?? undefined,
		createdAt: typeof d.createdAt === 'string' ? d.createdAt : new Date(d.createdAt).toISOString()
	}));
}

export async function createItem(input: CreateItemInput): Promise<Item> {
	const res = await fetch('/api/items', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify(input)
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.error || 'Failed to create item');
	}
	const data = await res.json();
	return {
		...data,
		description: data.description ?? undefined,
		createdAt: typeof data.createdAt === 'string' ? data.createdAt : new Date(data.createdAt).toISOString()
	};
}

export async function toggleItem(id: string, completed: boolean): Promise<Item> {
	const res = await fetch('/api/items', {
		method: 'PATCH',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ id, completed })
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.error || 'Failed to update item');
	}
	const data = await res.json();
	return {
		...data,
		description: data.description ?? undefined,
		createdAt: typeof data.createdAt === 'string' ? data.createdAt : new Date(data.createdAt).toISOString()
	};
}

export async function deleteItem(id: string): Promise<void> {
	const res = await fetch(`/api/items?id=${encodeURIComponent(id)}`, {
		method: 'DELETE'
	});
	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.error || 'Failed to delete item');
	}
}

export const itemsApi: ItemsApi = { fetchItems, createItem, toggleItem, deleteItem };
