<!-- Inline message box with a non-colour icon (info / warning / error / success). -->
<script lang="ts">
	import type { Snippet } from 'svelte';
	import InfoIcon from '@lucide/svelte/icons/info';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import CircleXIcon from '@lucide/svelte/icons/circle-x';
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';

	type Props = {
		tone?: 'info' | 'warning' | 'error' | 'success';
		title?: string;
		children?: Snippet;
		actions?: Snippet;
		role?: 'alert' | 'status';
		testid?: string;
	};
	let { tone = 'info', title, children, actions, role, testid }: Props = $props();

	const STYLE = {
		info: 'border-sky-200 bg-sky-50 text-sky-950',
		warning: 'border-amber-300 bg-amber-50 text-amber-950',
		error: 'border-red-300 bg-red-50 text-red-950',
		success: 'border-emerald-300 bg-emerald-50 text-emerald-950'
	} as const;
	const ICON = {
		info: InfoIcon,
		warning: TriangleAlertIcon,
		error: CircleXIcon,
		success: CircleCheckIcon
	};
	const Icon = $derived(ICON[tone]);
</script>

<div class={['flex gap-3 rounded-lg border p-3 text-sm', STYLE[tone]]} {role} data-testid={testid}>
	<Icon class="mt-0.5 size-5 shrink-0" aria-hidden="true" />
	<div class="flex min-w-0 flex-1 flex-col gap-1">
		{#if title}<p class="font-semibold">{title}</p>{/if}
		{@render children?.()}
		{#if actions}<div class="mt-2 flex flex-wrap gap-2">{@render actions()}</div>{/if}
	</div>
</div>
