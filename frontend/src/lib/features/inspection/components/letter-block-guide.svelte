<!-- Illustration of the 26-key letter block with the four reference slots (Q, P, M, Z by position). -->
<script lang="ts">
	import { KEY_HALF_U, LETTER_ROWS, REFERENCE_SLOTS, slotCenterU } from '../geometry';

	type Props = {
		/** Index (0–3) of the reference point to place next; -1 = none. */
		active?: number;
		/** Number of reference points already placed. */
		done?: number;
	};

	let { active = -1, done = 0 }: Props = $props();

	const PAD = 0.15;
	const keys = LETTER_ROWS.flatMap((letters, row) =>
		[...letters].map((label, col) => {
			const [cx, cy] = slotCenterU(row, col);
			const ref = REFERENCE_SLOTS.findIndex((r) => r.row === row && r.col === col);
			return { id: `r${row}c${col}`, label, cx, cy, ref };
		})
	);
	const h = KEY_HALF_U;
	const viewBox = `${-h - PAD} ${-h - PAD} ${9 + 2 * h + 2 * PAD} ${2 + 2 * h + 2 * PAD}`;
</script>

<svg
	{viewBox}
	class="h-auto w-full max-w-md select-none"
	role="img"
	aria-label="ภาพประกอบบล็อกตัวอักษร: จุดที่ 1 ช่อง Q ซ้ายบน, จุดที่ 2 ช่อง P ขวาบน, จุดที่ 3 ช่อง M ขวาล่าง, จุดที่ 4 ช่อง Z ซ้ายล่าง"
>
	<polygon
		points={REFERENCE_SLOTS.map((r) => slotCenterU(r.row, r.col).join(',')).join(' ')}
		class="fill-sky-500/10 stroke-sky-600"
		stroke-width="0.04"
		stroke-dasharray="0.12 0.08"
	/>
	{#each keys as k (k.id)}
		{@const isRef = k.ref >= 0}
		{@const isActive = isRef && k.ref === active}
		{@const isDone = isRef && k.ref < done}
		<rect
			x={k.cx - h}
			y={k.cy - h}
			width={2 * h}
			height={2 * h}
			rx="0.12"
			class={[
				'stroke-[0.03]',
				isActive
					? 'fill-sky-500 stroke-sky-700'
					: isDone
						? 'fill-sky-200 stroke-sky-600'
						: isRef
							? 'fill-sky-50 stroke-sky-600'
							: 'fill-muted stroke-border'
			]}
		/>
		<text
			x={k.cx}
			y={k.cy + 0.13}
			text-anchor="middle"
			font-size="0.38"
			class={isActive
				? 'fill-white font-bold'
				: isRef
					? 'fill-sky-900 font-semibold'
					: 'fill-muted-foreground'}>{k.label}</text
		>
		{#if isRef}
			<circle cx={k.cx + h - 0.05} cy={k.cy - h + 0.05} r="0.2" class="fill-sky-700" />
			<text
				x={k.cx + h - 0.05}
				y={k.cy - h + 0.13}
				text-anchor="middle"
				font-size="0.24"
				class="fill-white font-bold">{k.ref + 1}</text
			>
		{/if}
	{/each}
</svg>
