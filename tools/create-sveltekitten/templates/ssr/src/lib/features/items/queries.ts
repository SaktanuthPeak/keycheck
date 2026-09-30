import { createQuery, createMutation, useQueryClient } from '@tanstack/svelte-query';
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
			toast.success(`Created "${newItem.title}"`);
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
					? `Completed "${updatedItem.title}"`
					: `Marked "${updatedItem.title}" as active`
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
