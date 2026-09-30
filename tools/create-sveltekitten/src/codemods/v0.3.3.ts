import type { Codemod } from './index.js';

const PORT_FILE = `import type { Item, CreateItemInput } from './schema';

export interface ItemsApi {
	fetchItems(): Promise<Item[]>;
	createItem(input: CreateItemInput): Promise<Item>;
	toggleItem(id: string, completed: boolean): Promise<Item>;
	deleteItem(id: string): Promise<void>;
}
`;

const OLD_API_IMPORT = `import type { Item, CreateItemInput } from './schema';`;
const NEW_API_IMPORT = `import type { Item, CreateItemInput } from './schema';
import type { ItemsApi } from './port';`;

const NEW_QUERIES_FILE = `import { createQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
import { itemsApi as defaultItemsApi } from './api';
import type { ItemsApi } from './port';
import type { CreateItemInput, Item } from './schema';
import { toast } from 'svelte-sonner';

export const itemKeys = {
	all: ['items'] as const,
	lists: () => [...itemKeys.all, 'list'] as const,
	detail: (id: string) => [...itemKeys.all, 'detail', id] as const
};

export function useItems(
	initialDataGetter?: () => Item[] | undefined,
	itemsApi: ItemsApi = defaultItemsApi
) {
	return createQuery(() => ({
		queryKey: itemKeys.lists(),
		queryFn: itemsApi.fetchItems,
		initialData: initialDataGetter ? initialDataGetter() : undefined,
		staleTime: 1000 * 60
	}));
}

export function useCreateItem(itemsApi: ItemsApi = defaultItemsApi) {
	const queryClient = useQueryClient();
	return createMutation(() => ({
		mutationFn: (input: CreateItemInput) => itemsApi.createItem(input),
		onSuccess: (newItem) => {
			queryClient.invalidateQueries({ queryKey: itemKeys.lists() });
			toast.success(\`Created "\${newItem.title}"\`);
		},
		onError: (error: Error) => {
			toast.error(error.message || 'Failed to create item');
		}
	}));
}

export function useToggleItem(itemsApi: ItemsApi = defaultItemsApi) {
	const queryClient = useQueryClient();
	return createMutation(() => ({
		mutationFn: ({ id, completed }: { id: string; completed: boolean }) =>
			itemsApi.toggleItem(id, completed),
		onSuccess: (updatedItem) => {
			queryClient.invalidateQueries({ queryKey: itemKeys.lists() });
			toast.success(
				updatedItem.completed
					? \`Completed "\${updatedItem.title}"\`
					: \`Marked "\${updatedItem.title}" as active\`
			);
		},
		onError: (error: Error) => {
			toast.error(error.message || 'Failed to update item');
		}
	}));
}

export function useDeleteItem(itemsApi: ItemsApi = defaultItemsApi) {
	const queryClient = useQueryClient();
	return createMutation(() => ({
		mutationFn: (id: string) => itemsApi.deleteItem(id),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: itemKeys.lists() });
			toast.success('Item deleted');
		},
		onError: (error: Error) => {
			toast.error(error.message || 'Failed to delete item');
		}
	}));
}
`;

const OLD_INDEX_LINE = `export * as itemsApi from './api';`;
const NEW_INDEX_LINES = `export * as itemsApi from './api';
export type { ItemsApi } from './port';`;

const codemod: Codemod = {
	from: '0.3.2',
	to: '0.3.3',
	transforms: [
		{
			// Explicit ItemsApi port: queries.ts previously imported api.ts as a
			// concrete module (`import * as api from './api'`) with no interface,
			// so nothing could be swapped or mocked without editing queries.ts.
			file: 'src/lib/features/items/port.ts',
			create: true,
			transform: () => PORT_FILE
		},
		{
			file: 'src/lib/features/items/api.ts',
			transform: (content) => {
				let next = content;
				if (!next.includes("from './port'") && next.includes(OLD_API_IMPORT)) {
					next = next.replace(OLD_API_IMPORT, NEW_API_IMPORT);
				}
				if (!next.includes('export const itemsApi: ItemsApi')) {
					next = `${next.trimEnd()}\n\nexport const itemsApi: ItemsApi = { fetchItems, createItem, toggleItem, deleteItem };\n`;
				}
				return next;
			}
		},
		{
			file: 'src/lib/features/items/queries.ts',
			transform: (content) => {
				if (!content.includes("import * as api from './api';")) return content;
				return NEW_QUERIES_FILE;
			}
		},
		{
			file: 'src/lib/features/items/index.ts',
			transform: (content) => {
				if (content.includes("export type { ItemsApi }")) return content;
				if (!content.includes(OLD_INDEX_LINE)) return content;
				return content.replace(OLD_INDEX_LINE, NEW_INDEX_LINES);
			}
		}
	]
};

export default codemod;
