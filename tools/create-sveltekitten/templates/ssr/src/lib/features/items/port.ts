import type { Item, CreateItemInput } from './schema';

export interface ItemsApi {
	fetchItems(): Promise<Item[]>;
	createItem(input: CreateItemInput): Promise<Item>;
	toggleItem(id: string, completed: boolean): Promise<Item>;
	deleteItem(id: string): Promise<void>;
}
