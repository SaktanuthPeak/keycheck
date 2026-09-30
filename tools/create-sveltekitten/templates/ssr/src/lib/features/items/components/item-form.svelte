<script lang="ts">
	import { Input } from '$lib/components/ui/input';
	import { Button } from '$lib/components/ui/button';
	import { Label } from '$lib/components/ui/label';
	import PlusIcon from '@lucide/svelte/icons/plus';
	import LoaderCircle from '@lucide/svelte/icons/loader-circle';
	import { createItemSchema } from '../schema';
	import { useCreateItem } from '../queries';

	const createMutation = useCreateItem();

	let title = $state('');
	let description = $state('');
	let error = $state<string | null>(null);

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = null;

		const result = createItemSchema.safeParse({
			title: title.trim(),
			description: description.trim() || undefined
		});

		if (!result.success) {
			error = result.error.issues[0]?.message ?? 'Invalid input';
			return;
		}

		createMutation.mutate(result.data, {
			onSuccess: () => {
				title = '';
				description = '';
				error = null;
			}
		});
	}
</script>

<form onsubmit={handleSubmit} class="space-y-3 rounded-lg border bg-card p-4">
	<h3 class="text-sm font-semibold text-foreground">Add New Item</h3>

	<div class="space-y-1">
		<Label for="item-title" class="text-xs">Title *</Label>
		<Input
			id="item-title"
			placeholder="e.g. Design database schema"
			bind:value={title}
			disabled={createMutation.isPending}
		/>
	</div>

	<div class="space-y-1">
		<Label for="item-desc" class="text-xs">Description (optional)</Label>
		<Input
			id="item-desc"
			placeholder="e.g. Add users and items tables"
			bind:value={description}
			disabled={createMutation.isPending}
		/>
	</div>

	{#if error}
		<p class="text-xs text-destructive">{error}</p>
	{/if}

	<Button type="submit" size="sm" class="w-full" disabled={createMutation.isPending || !title.trim()}>
		{#if createMutation.isPending}
			<LoaderCircle class="h-4 w-4 animate-spin" />
			Adding...
		{:else}
			<PlusIcon class="h-4 w-4" />
			Add Item
		{/if}
	</Button>
</form>
