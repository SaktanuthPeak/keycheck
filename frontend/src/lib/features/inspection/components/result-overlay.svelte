<!--
	Result overlay (Spec §10.5). The SVG viewBox equals the real image size and the wrapper keeps the
	image aspect ratio, so normalised polygons stay aligned at any rendered size. Status is shown with
	colour + shape + glyph (never colour alone); polygons from the layout fallback are dashed.
-->
<script lang="ts">
	import { centroid, polygonArea } from '../geometry';
	import { candidateHint, SLOT_STATUS_TEXT } from '../messages';
	import type { Slot } from '../schema';

	type Props = {
		imageUrl: string;
		width: number;
		height: number;
		slots: Slot[];
		selectedId?: string | null;
		onselect?: (slotId: string) => void;
		/** Image deleted by retention: draw polygons on a neutral background. */
		expired?: boolean;
	};

	let {
		imageUrl,
		width,
		height,
		slots,
		selectedId = null,
		onselect,
		expired = false
	}: Props = $props();

	let imgFailed = $state(false);
	const showImage = $derived(!expired && !imgFailed && !!imageUrl);

	const COLORS = {
		correct: { stroke: '#16a34a', fill: 'rgb(22 163 74 / 0.12)' },
		incorrect: { stroke: '#dc2626', fill: 'rgb(220 38 38 / 0.22)' },
		uncertain: { stroke: '#d97706', fill: 'rgb(245 158 11 / 0.22)' }
	} as const;

	const shapes = $derived(
		slots.map((s) => {
			const px = s.polygon.map(([x, y]) => [x * width, y * height] as const);
			const [cx, cy] = centroid(px);
			const size = Math.sqrt(polygonArea(px));
			return {
				slot: s,
				points: px.map(([x, y]) => `${x},${y}`).join(' '),
				cx,
				cy,
				r: Math.max(size * 0.22, Math.min(width, height) * 0.006)
			};
		})
	);
	// Draw the selected slot last so its outline is on top.
	const ordered = $derived(
		[...shapes].sort(
			(a, b) => Number(a.slot.slot_id === selectedId) - Number(b.slot.slot_id === selectedId)
		)
	);
	const dash = $derived(`${Math.max(width, height) * 0.006} ${Math.max(width, height) * 0.004}`);

	function onkeydown(e: KeyboardEvent, id: string) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onselect?.(id);
		}
	}
</script>

<div
	class="relative mx-auto overflow-hidden rounded-lg bg-muted"
	style:aspect-ratio="{width} / {height}"
	style:width="min(100%, calc(70svh * {width / height}))"
	data-testid="result-overlay"
>
	{#if showImage}
		<img
			src={imageUrl}
			alt="ภาพคีย์บอร์ดพร้อมกรอบผลตรวจ"
			class="absolute inset-0 block h-full w-full"
			draggable="false"
			onerror={() => (imgFailed = true)}
		/>
	{:else}
		<p
			class="absolute inset-x-0 top-2 mx-auto w-fit max-w-[90%] rounded bg-background/90 px-2 py-1 text-center text-xs text-muted-foreground"
		>
			ภาพถูกลบตามระยะเวลาเก็บรักษาแล้ว — แสดงเฉพาะกรอบตำแหน่ง
		</p>
	{/if}
	<svg
		class="absolute inset-0 h-full w-full"
		viewBox="0 0 {width} {height}"
		preserveAspectRatio="none"
		role="group"
		aria-label="กรอบผลตรวจรายช่องบนภาพ"
	>
		{#each ordered as { slot, points, cx, cy, r } (slot.slot_id)}
			{@const c = COLORS[slot.status]}
			{@const selected = slot.slot_id === selectedId}
			<g
				role="button"
				tabindex="-1"
				aria-label="ช่อง {slot.expected_label}: {SLOT_STATUS_TEXT[slot.status]}"
				aria-pressed={selected}
				data-slot-id={slot.slot_id}
				data-status={slot.status}
				data-selected={selected}
				data-source={slot.polygon_source}
				class="cursor-pointer outline-none"
				onclick={() => onselect?.(slot.slot_id)}
				onkeydown={(e) => onkeydown(e, slot.slot_id)}
			>
				{#if selected}
					<polygon
						{points}
						fill="none"
						stroke="white"
						stroke-width="9"
						vector-effect="non-scaling-stroke"
						stroke-linejoin="round"
					/>
				{/if}
				<polygon
					{points}
					fill={c.fill}
					stroke={c.stroke}
					stroke-width={selected ? 5 : slot.status === 'correct' ? 1.5 : 2.5}
					stroke-dasharray={slot.polygon_source === 'layout' ? dash : undefined}
					vector-effect="non-scaling-stroke"
					stroke-linejoin="round"
				/>
				{#if slot.status === 'incorrect'}
					<polygon
						points="{cx},{cy - r} {cx + r * 1.1},{cy + r * 0.8} {cx - r * 1.1},{cy + r * 0.8}"
						fill={c.stroke}
						stroke="white"
						stroke-width="1.5"
						vector-effect="non-scaling-stroke"
					/>
					<text
						x={cx}
						y={cy + r * 0.62}
						text-anchor="middle"
						font-size={r * 1.15}
						font-weight="700"
						fill="white">!</text
					>
				{:else if slot.status === 'uncertain'}
					<circle
						{cx}
						{cy}
						{r}
						fill={c.stroke}
						stroke="white"
						stroke-width="1.5"
						vector-effect="non-scaling-stroke"
					/>
					<text
						x={cx}
						y={cy + r * 0.42}
						text-anchor="middle"
						font-size={r * 1.2}
						font-weight="700"
						fill="white">{candidateHint(slot) ?? '?'}</text
					>
				{:else}
					<circle {cx} {cy} r={r * 0.75} fill={c.stroke} opacity="0.9" />
					<path
						d="M {cx - r * 0.38} {cy} L {cx - r * 0.08} {cy + r * 0.3} L {cx + r * 0.4} {cy -
							r * 0.3}"
						fill="none"
						stroke="white"
						stroke-width="2"
						stroke-linecap="round"
						stroke-linejoin="round"
						vector-effect="non-scaling-stroke"
					/>
				{/if}
			</g>
		{/each}
	</svg>
</div>
