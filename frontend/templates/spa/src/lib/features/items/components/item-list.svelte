<script lang="ts">
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Button } from '$lib/components/ui/button';
	import type { Item } from '../schema';
	import { useItems } from '../queries';
	import ItemCard from './item-card.svelte';
	import ItemEmptyState from './item-empty-state.svelte';
	import RotateCwIcon from '@lucide/svelte/icons/rotate-cw';

	interface Props {
		initialData?: Item[];
	}

	let { initialData }: Props = $props();

	const itemsQuery = useItems(() => initialData);

	let filter = $state<'all' | 'active' | 'completed'>('all');

	const items = $derived(itemsQuery.data ?? []);
	const totalCount = $derived(items.length);
	const activeCount = $derived(items.filter((i) => !i.completed).length);
	const completedCount = $derived(items.filter((i) => i.completed).length);

	const filteredItems = $derived(
		items.filter((item) => {
			if (filter === 'active') return !item.completed;
			if (filter === 'completed') return item.completed;
			return true;
		})
	);
</script>

<div class="space-y-4">
	<!-- Filter header -->
	<div class="flex items-center justify-between gap-2">
		<div class="flex items-center gap-1 rounded-lg border bg-muted/30 p-1 text-xs">
			<button
				type="button"
				class="cursor-pointer rounded-md px-2.5 py-1 font-medium transition-colors {filter === 'all'
					? 'bg-background text-foreground shadow-xs'
					: 'text-muted-foreground hover:text-foreground'}"
				onclick={() => (filter = 'all')}
			>
				All ({totalCount})
			</button>
			<button
				type="button"
				class="cursor-pointer rounded-md px-2.5 py-1 font-medium transition-colors {filter === 'active'
					? 'bg-background text-foreground shadow-xs'
					: 'text-muted-foreground hover:text-foreground'}"
				onclick={() => (filter = 'active')}
			>
				Active ({activeCount})
			</button>
			<button
				type="button"
				class="cursor-pointer rounded-md px-2.5 py-1 font-medium transition-colors {filter === 'completed'
					? 'bg-background text-foreground shadow-xs'
					: 'text-muted-foreground hover:text-foreground'}"
				onclick={() => (filter = 'completed')}
			>
				Completed ({completedCount})
			</button>
		</div>

		<Button
			variant="ghost"
			size="icon"
			class="size-8 text-muted-foreground hover:text-foreground"
			onclick={() => itemsQuery.refetch()}
			disabled={itemsQuery.isFetching}
			aria-label="Refresh items"
		>
			<RotateCwIcon class="h-3.5 w-3.5 {itemsQuery.isFetching ? 'animate-spin' : ''}" />
		</Button>
	</div>

	<!-- Query States -->
	{#if itemsQuery.isLoading}
		<div class="space-y-2">
			<Skeleton class="h-16 w-full rounded-lg" />
			<Skeleton class="h-16 w-full rounded-lg" />
			<Skeleton class="h-16 w-full rounded-lg" />
		</div>
	{:else if itemsQuery.isError}
		<div class="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-center">
			<p class="text-sm text-destructive font-medium">Failed to load items</p>
			<p class="text-xs text-muted-foreground mt-1">{itemsQuery.error?.message}</p>
			<Button
				variant="outline"
				size="sm"
				class="mt-3"
				onclick={() => itemsQuery.refetch()}
			>
				Try Again
			</Button>
		</div>
	{:else if filteredItems.length === 0}
		<ItemEmptyState {filter} />
	{:else}
		<div class="space-y-2">
			{#each filteredItems as item (item.id)}
				<ItemCard {item} />
			{/each}
		</div>
	{/if}
</div>
