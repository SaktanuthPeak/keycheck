<!-- Job progress as named steps (Spec §10.6: no unmeasured percentages). -->
<script lang="ts">
	import CheckIcon from '@lucide/svelte/icons/check';
	import LoaderCircleIcon from '@lucide/svelte/icons/loader-circle';
	import { STAGE_TEXT, STAGES } from '../messages';
	import type { InspectionStatus, Stage } from '../schema';

	type Props = { status: InspectionStatus; stage: Stage | null };
	let { status, stage }: Props = $props();

	const steps = [
		{ key: 'queued', text: 'รอคิวประมวลผล' },
		...STAGES.map((s) => ({ key: s, text: STAGE_TEXT[s] }))
	];
	const current = $derived(
		status === 'queued'
			? 0
			: status === 'processing'
				? 1 + Math.max(0, STAGES.indexOf(stage ?? 'rectifying'))
				: steps.length
	);
	const currentText = $derived(steps[Math.min(current, steps.length - 1)].text);
</script>

<div class="flex flex-col gap-3">
	<p class="text-lg font-semibold" aria-live="polite" data-testid="stage-text">
		{status === 'queued' ? 'รอคิวประมวลผล' : `กำลังประมวลผล: ${currentText}`}
	</p>
	<ol class="flex flex-col gap-2">
		{#each steps as step, i (step.key)}
			{@const state = i < current ? 'done' : i === current ? 'current' : 'pending'}
			<li
				class={[
					'flex items-center gap-2 text-sm',
					state === 'pending' && 'text-muted-foreground',
					state === 'current' && 'font-semibold'
				]}
				aria-current={state === 'current' ? 'step' : undefined}
			>
				<span
					class={[
						'flex size-6 items-center justify-center rounded-full border',
						state === 'done' && 'border-emerald-600 bg-emerald-600 text-white',
						state === 'current' && 'border-sky-600 text-sky-700'
					]}
					aria-hidden="true"
				>
					{#if state === 'done'}
						<CheckIcon class="size-4" />
					{:else if state === 'current'}
						<LoaderCircleIcon class="size-4 animate-spin" />
					{:else}
						{i + 1}
					{/if}
				</span>
				{step.text}
				<span class="sr-only"
					>{state === 'done' ? '(เสร็จแล้ว)' : state === 'current' ? '(กำลังทำ)' : '(รอ)'}</span
				>
			</li>
		{/each}
	</ol>
</div>
