import type { Item, CreateItemInput } from './schema';
import type { ItemsApi } from './port';

/**
 * In-memory store providing an immediate working example out-of-the-box.
 * Replace with your backend API calls (e.g. via client) when connecting to real endpoints.
 */
let mockItems: Item[] = [
	{
		id: '1',
		title: 'Explore SvelteKitten template',
		description: 'Learn about Svelte 5 runes, TanStack Query, and feature structure.',
		completed: true,
		createdAt: new Date(Date.now() - 3600000).toISOString()
	},
	{
		id: '2',
		title: 'Build your awesome feature',
		description: 'Duplicate this feature folder or replace it with your domain logic.',
		completed: false,
		createdAt: new Date().toISOString()
	}
];

export async function fetchItems(): Promise<Item[]> {
	await new Promise((resolve) => setTimeout(resolve, 200));
	return [...mockItems];
}

export async function createItem(input: CreateItemInput): Promise<Item> {
	await new Promise((resolve) => setTimeout(resolve, 200));
	const newItem: Item = {
		id: Math.random().toString(36).substring(2, 9),
		title: input.title,
		description: input.description,
		completed: false,
		createdAt: new Date().toISOString()
	};
	mockItems = [newItem, ...mockItems];
	return newItem;
}

export async function toggleItem(id: string, completed: boolean): Promise<Item> {
	await new Promise((resolve) => setTimeout(resolve, 150));
	const item = mockItems.find((i) => i.id === id);
	if (!item) throw new Error('Item not found');
	item.completed = completed;
	return { ...item };
}

export async function deleteItem(id: string): Promise<void> {
	await new Promise((resolve) => setTimeout(resolve, 150));
	mockItems = mockItems.filter((i) => i.id !== id);
}

export const itemsApi: ItemsApi = { fetchItems, createItem, toggleItem, deleteItem };
