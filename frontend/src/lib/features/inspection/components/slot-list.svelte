<!--
	Per-slot result list (Spec §10.5): incorrect and uncertain first, correct slots collapsed.
	Each row is a toggle button; Enter/Space selects, ArrowUp/ArrowDown/Home/End move focus.
-->
<script lang="ts">
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import CircleQuestionMarkIcon from '@lucide/svelte/icons/circle-question-mark';
	import { candidateHint, percent, reasonText, SLOT_STATUS_TEXT } from '../messages';
	import type { Slot, SlotStatus } from '../schema';

	type Props = {
		slots: Slot[];
		selectedId?: string | null;
		onselect: (slotId: string | null) => void;
	};

	let { slots, selectedId = null, onselect }: Props = $props();

	let list = $state<HTMLElement | null>(null);
	let showCorrect = $state(false);

	const ORDER: Record<SlotStatus, number> = { incorrect: 0, uncertain: 1, correct: 2 };
	const byOrder = (a: Slot, b: Slot) =>
		ORDER[a.status] - ORDER[b.status] || a.row - b.row || a.col - b.col;

	const problems = $derived(slots.filter((s) => s.status !== 'correct').sort(byOrder));
	const correct = $derived(slots.filter((s) => s.status === 'correct').sort(byOrder));
	const selectedIsCorrect = $derived(correct.some((s) => s.slot_id === selectedId));
	const correctVisible = $derived(showCorrect || selectedIsCorrect);

	const STYLE: Record<SlotStatus, string> = {
		incorrect: 'border-red-300 bg-red-50 text-red-950',
		uncertain: 'border-amber-300 bg-amber-50 text-amber-950',
		correct: 'border-emerald-200 bg-emerald-50/60 text-emerald-950'
	};

	function onkeydown(e: KeyboardEvent) {
		const items = [...(list?.querySelectorAll<HTMLButtonElement>('button[data-slot-id]') ?? [])];
		const i = items.indexOf(document.activeElement as HTMLButtonElement);
		if (i < 0) return;
		const to =
			e.key === 'ArrowDown'
				? Math.min(items.length - 1, i + 1)
				: e.key === 'ArrowUp'
					? Math.max(0, i - 1)
					: e.key === 'Home'
						? 0
						: e.key === 'End'
							? items.length - 1
							: -1;
		if (to < 0) return;
		e.preventDefault();
		items[to].focus();
	}
</script>

{#snippet row(s: Slot)}
	{@const selected = s.slot_id === selectedId}
	{@const hint = candidateHint(s)}
	<li>
		<button
			type="button"
			data-slot-id={s.slot_id}
			aria-pressed={selected}
			class={[
				'flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-shadow focus-visible:ring-[3px] focus-visible:ring-sky-400 focus-visible:outline-none',
				STYLE[s.status],
				selected && 'ring-2 ring-sky-600'
			]}
			onclick={() => onselect(selected ? null : s.slot_id)}
		>
			<span class="mt-0.5 shrink-0" aria-hidden="true">
				{#if s.status === 'incorrect'}
					<TriangleAlertIcon class="size-5 text-red-600" />
				{:else if s.status === 'uncertain'}
					<CircleQuestionMarkIcon class="size-5 text-amber-600" />
				{:else}
					<CircleCheckIcon class="size-5 text-emerald-600" />
				{/if}
			</span>
			<span class="min-w-0 flex-1">
				<span class="flex flex-wrap items-baseline gap-x-2">
					<span class="font-semibold">
						{#if hint}
							ช่อง {s.expected_label}: ควรเป็น {s.expected_label} / น่าจะเป็น {hint}
							<span class="font-normal">({percent(s.ocr_score)})</span>
						{:else}
							ช่อง {s.expected_label}: ควรเป็น {s.expected_label} / พบ {s.observed_label ??
								'อ่านไม่ได้'}
						{/if}
					</span>
					<span class="text-xs font-medium">({SLOT_STATUS_TEXT[s.status]})</span>
					{#if s.is_reference}
						<span class="rounded bg-sky-100 px-1.5 text-xs text-sky-800">จุดอ้างอิง</span>
					{/if}
				</span>
				<span class="mt-0.5 block text-sm opacity-90" data-testid="slot-reason">
					{#if hint}
						ระบบเห็นเป็น {hint} แต่ยังมั่นใจไม่พอจะยืนยัน — โปรดดูปุ่มนี้ด้วยตาอีกครั้ง
					{:else}
						{reasonText(s.reason)}
					{/if}
				</span>
				{#if s.polygon_source === 'layout'}
					<span class="mt-0.5 block text-xs opacity-75">
						กรอบเส้นประ = ตำแหน่งตามแบบ ไม่ได้มาจากการตรวจจับปุ่ม
					</span>
				{/if}
			</span>
		</button>
	</li>
{/snippet}

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div bind:this={list} class="flex flex-col gap-3" {onkeydown} data-testid="slot-list">
	{#if problems.length}
		<ul class="flex flex-col gap-2" aria-label="ช่องที่ผิดหรือไม่แน่ใจ">
			{#each problems as s (s.slot_id)}
				{@render row(s)}
			{/each}
		</ul>
	{:else}
		<p class="text-sm text-muted-foreground">ไม่มีช่องที่ผิดหรือไม่แน่ใจ</p>
	{/if}

	{#if correct.length}
		<button
			type="button"
			class="self-start text-sm font-medium text-sky-800 underline underline-offset-4"
			aria-expanded={correctVisible}
			onclick={() => {
				if (correctVisible && selectedIsCorrect) onselect(null);
				showCorrect = !correctVisible;
			}}
		>
			{correctVisible ? 'ซ่อน' : 'แสดง'}ช่องที่ถูกต้อง ({correct.length} ช่อง)
		</button>
		{#if correctVisible}
			<ul class="grid gap-2 sm:grid-cols-2" aria-label="ช่องที่ถูกต้อง">
				{#each correct as s (s.slot_id)}
					{@render row(s)}
				{/each}
			</ul>
		{/if}
	{/if}
</div>
