<script lang="ts">
	import { ItemList, ItemForm } from '$lib/features/items';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
</script>

<svelte:head>
	<title>Items Example - SvelteKitten</title>
</svelte:head>

<div class="container mx-auto max-w-4xl p-6 space-y-6">
	<!-- Example feature header -->
	<div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b pb-4">
		<div>
			<div class="flex items-center gap-2">
				<h1 class="text-2xl font-bold tracking-tight">Items Tracker</h1>
				<span class="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-medium text-primary">
					<SparklesIcon class="h-3 w-3" />
					Example Feature
				</span>
			</div>
			<p class="text-sm text-muted-foreground mt-1">
				A complete reference showing Svelte 5 runes, Zod schemas, and TanStack Query mutations.
			</p>
		</div>
	</div>

	<!-- Main content grid -->
	<div class="grid gap-6 md:grid-cols-3">
		<div class="md:col-span-1">
			<ItemForm />
		</div>
		<div class="md:col-span-2">
			<ItemList />
		</div>
	</div>
</div>
