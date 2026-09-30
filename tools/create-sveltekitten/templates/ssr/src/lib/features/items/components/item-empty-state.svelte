<script lang="ts">
	import InboxIcon from '@lucide/svelte/icons/inbox';

	interface Props {
		filter: 'all' | 'active' | 'completed';
	}

	let { filter }: Props = $props();

	const message = $derived(
		filter === 'completed'
			? 'No completed items yet.'
			: filter === 'active'
				? 'No active items. All tasks done!'
				: 'No items created yet. Add one to get started!'
	);
</script>

<div class="flex flex-col items-center justify-center rounded-lg border border-dashed p-8 text-center">
	<InboxIcon class="h-10 w-10 text-muted-foreground/50 mb-3" />
	<p class="text-sm font-medium text-foreground">{message}</p>
	<p class="text-xs text-muted-foreground mt-1">
		Use the form to create new tasks or toggle existing ones.
	</p>
</div>
