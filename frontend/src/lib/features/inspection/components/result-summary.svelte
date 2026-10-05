<!--
	Summary (Spec §10.5): "processing finished" is separate from "all keys correct"; never claims all
	correct while any slot is uncertain. Suggestions are shown only as returned (already confirmed).
-->
<script lang="ts">
	import CircleCheckIcon from '@lucide/svelte/icons/circle-check';
	import TriangleAlertIcon from '@lucide/svelte/icons/triangle-alert';
	import CircleQuestionMarkIcon from '@lucide/svelte/icons/circle-question-mark';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import { warningInfo } from '../messages';
	import type { Inspection, Slot } from '../schema';
	import Notice from './notice.svelte';

	type Props = { inspection: Inspection; simulated?: boolean };
	let { inspection, simulated = false }: Props = $props();

	const summary = $derived(
		inspection.summary ?? {
			total_slots: inspection.slots.length,
			correct: inspection.slots.filter((s) => s.status === 'correct').length,
			incorrect: inspection.slots.filter((s) => s.status === 'incorrect').length,
			uncertain: inspection.slots.filter((s) => s.status === 'uncertain').length
		}
	);
	const verdict = $derived(
		summary.incorrect > 0 ? 'incorrect' : summary.uncertain > 0 ? 'uncertain' : 'all_correct'
	);
	const bySlot = $derived(new Map<string, Slot>(inspection.slots.map((s) => [s.slot_id, s])));
	const label = (id: string) => bySlot.get(id)?.expected_label ?? id;
	const observed = (id: string) => bySlot.get(id)?.observed_label ?? '?';
</script>

<section class="flex flex-col gap-4" aria-labelledby="summary-heading">
	<div class="flex flex-wrap items-center gap-2">
		<h2 id="summary-heading" class="text-xl font-bold">ผลตรวจ</h2>
		<span
			class="inline-flex items-center gap-1 rounded-full border border-sky-300 bg-sky-50 px-2.5 py-0.5 text-sm text-sky-900"
			data-testid="processing-done"
		>
			<CircleCheckIcon class="size-4" aria-hidden="true" /> ประมวลผลเสร็จ
		</span>
		{#if simulated}
			<span
				class="inline-flex items-center gap-1 rounded-full border border-fuchsia-300 bg-fuchsia-50 px-2.5 py-0.5 text-sm text-fuchsia-900"
			>
				<FlaskConicalIcon class="size-4" aria-hidden="true" /> ผลจำลอง
			</span>
		{/if}
	</div>

	{#if verdict === 'all_correct'}
		<Notice tone="success" title="ทุกปุ่มถูกต้อง" testid="verdict" role="status">
			<p>
				ตรวจครบ {summary.total_slots} ช่อง ไม่พบปุ่มที่อยู่ผิดตำแหน่ง และไม่มีช่องที่ระบบไม่แน่ใจ
			</p>
		</Notice>
	{:else if verdict === 'incorrect'}
		<Notice
			tone="error"
			title="พบปุ่มที่อยู่ผิดตำแหน่ง {summary.incorrect} ช่อง"
			testid="verdict"
			role="status"
		>
			{#if summary.uncertain > 0}
				<p>
					และมีอีก {summary.uncertain} ช่องที่ระบบยืนยันไม่ได้ จึงยังสรุปไม่ได้ว่าช่องอื่นถูกทั้งหมด
				</p>
			{/if}
		</Notice>
	{:else}
		<Notice tone="warning" title="ยังยืนยันไม่ได้ว่าทุกปุ่มถูกต้อง" testid="verdict" role="status">
			<p>
				ไม่พบปุ่มที่ผิด แต่มี {summary.uncertain} ช่องที่ระบบไม่แน่ใจ แนะนำให้ตรวจช่องเหล่านั้นด้วยตาเอง
				หรือถ่ายภาพใหม่ให้ชัดขึ้น
			</p>
		</Notice>
	{/if}

	<dl class="grid grid-cols-3 gap-2 text-center" data-testid="counts">
		<div class="rounded-lg border border-emerald-200 bg-emerald-50 p-2 text-emerald-950">
			<dt class="flex items-center justify-center gap-1 text-sm">
				<CircleCheckIcon class="size-4" aria-hidden="true" /> ถูก
			</dt>
			<dd class="text-2xl font-bold" data-testid="count-correct">{summary.correct}</dd>
		</div>
		<div class="rounded-lg border border-red-200 bg-red-50 p-2 text-red-950">
			<dt class="flex items-center justify-center gap-1 text-sm">
				<TriangleAlertIcon class="size-4" aria-hidden="true" /> ผิด
			</dt>
			<dd class="text-2xl font-bold" data-testid="count-incorrect">{summary.incorrect}</dd>
		</div>
		<div class="rounded-lg border border-amber-200 bg-amber-50 p-2 text-amber-950">
			<dt class="flex items-center justify-center gap-1 text-sm">
				<CircleQuestionMarkIcon class="size-4" aria-hidden="true" /> ไม่แน่ใจ
			</dt>
			<dd class="text-2xl font-bold" data-testid="count-uncertain">{summary.uncertain}</dd>
		</div>
	</dl>

	{#if inspection.suggestions.length}
		<div class="flex flex-col gap-2" data-testid="suggestions">
			<h3 class="font-semibold">คำแนะนำการแก้ไข</h3>
			<ul class="flex flex-col gap-2">
				{#each inspection.suggestions as sug (sug.slots.join('-'))}
					<li class="rounded-lg border bg-card p-3 text-sm">
						{#if sug.type === 'swap_pair' && sug.slots.length === 2}
							<p class="font-medium">
								สลับปุ่มในช่อง {label(sug.slots[0])} กับช่อง {label(sug.slots[1])}
							</p>
							<p class="text-muted-foreground">
								ช่อง {label(sug.slots[0])} พบ {observed(sug.slots[0])} และช่อง {label(sug.slots[1])} พบ
								{observed(sug.slots[1])}
							</p>
						{:else}
							<p class="font-medium">ปุ่ม {sug.slots.length} ตัวอยู่ผิดที่แบบวนกัน ย้ายตามนี้:</p>
							<ul class="mt-1 list-disc pl-5 text-muted-foreground">
								{#each sug.slots as id (id)}
									<li>ย้ายปุ่ม {observed(id)} จากช่อง {label(id)} ไปไว้ที่ช่อง {observed(id)}</li>
								{/each}
							</ul>
						{/if}
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	{#if inspection.warnings.length}
		<div class="flex flex-col gap-2" data-testid="warnings">
			{#each inspection.warnings as code (code)}
				{@const w = warningInfo(code)}
				<Notice tone={code === 'proxy_model' ? 'info' : 'warning'} title={w.title}>
					<p>{w.detail}</p>
				</Notice>
			{/each}
		</div>
	{/if}
</section>
