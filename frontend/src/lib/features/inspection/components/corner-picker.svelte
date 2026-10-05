<!--
	Reference-point picker (Spec §10.4). Controlled: `points` are normalised 0–1 on the backend-oriented
	image, order TL, TR, BR, BL = centres of slots Q, P, M, Z by position. Tap to place, drag to adjust,
	arrow keys to nudge. Parents must re-create this component (e.g. {#key imageId}) when the image changes
	so points and history from another image are never reused.
-->
<script lang="ts">
	import { tick } from 'svelte';
	import Undo2Icon from '@lucide/svelte/icons/undo-2';
	import RotateCcwIcon from '@lucide/svelte/icons/rotate-ccw';
	import { Button } from '$lib/components/ui/button';
	import { clamp01, REFERENCE_SLOTS, validateQuad, type Pt } from '../geometry';
	import { QUAD_ERROR_TEXT } from '../messages';
	import LetterBlockGuide from './letter-block-guide.svelte';

	type Props = {
		imageUrl: string;
		points: Pt[];
		onchange: (points: Pt[]) => void;
		disabled?: boolean;
		onimageerror?: () => void;
	};

	let { imageUrl, points, onchange, disabled = false, onimageerror }: Props = $props();

	const POSITION_TEXT = [
		'ปุ่มซ้ายสุดของแถวตัวอักษรบน',
		'ปุ่มขวาสุดของแถวตัวอักษรบน',
		'ปุ่มขวาสุดของแถวตัวอักษรล่าง',
		'ปุ่มซ้ายสุดของแถวตัวอักษรล่าง'
	];
	// Default keyboard placement (roughly where a centred letter block would be).
	const KEYBOARD_DEFAULTS: Pt[] = [
		[0.2, 0.35],
		[0.8, 0.35],
		[0.65, 0.65],
		[0.25, 0.65]
	];
	const LOUPE = 120;
	const ZOOM = 3;

	let surface = $state<HTMLDivElement | null>(null);
	let loaded = $state(false);
	let history = $state.raw<Pt[][]>([]);
	let drag = $state<{ index: number; pointerId: number; moved: boolean; added: boolean } | null>(
		null
	);
	let box = $state({ w: 0, h: 0 });

	const next = $derived(points.length < 4 ? points.length : -1);
	const error = $derived(points.length === 4 ? validateQuad(points) : null);
	const loupe = $derived.by(() => {
		if (!drag || !box.w) return null;
		const [x, y] = points[drag.index] ?? [0, 0];
		const right = x < 0.5 && y < 0.5;
		return {
			x,
			y,
			side: right ? 'right' : 'left',
			bgSize: `${box.w * ZOOM}px ${box.h * ZOOM}px`,
			bgPos: `${LOUPE / 2 - x * box.w * ZOOM}px ${LOUPE / 2 - y * box.h * ZOOM}px`
		};
	});

	function commit(nextPoints: Pt[], record = true) {
		if (record) history = [...history.slice(-49), points];
		onchange(nextPoints);
	}

	function toNorm(e: PointerEvent): Pt {
		const r = surface!.getBoundingClientRect();
		return [clamp01((e.clientX - r.left) / r.width), clamp01((e.clientY - r.top) / r.height)];
	}

	function nearest(p: Pt, maxPx: number): number {
		const r = surface!.getBoundingClientRect();
		let best = -1;
		let bestD = maxPx;
		points.forEach(([x, y], i) => {
			const d = Math.hypot((x - p[0]) * r.width, (y - p[1]) * r.height);
			if (d <= bestD) {
				best = i;
				bestD = d;
			}
		});
		return best;
	}

	function onpointerdown(e: PointerEvent) {
		if (disabled || !loaded || !surface || drag) return;
		if (e.pointerType === 'mouse' && e.button !== 0) return;
		const p = toNorm(e);
		const handle = (e.target as Element).closest<HTMLElement>('[data-handle]');
		let index = handle ? Number(handle.dataset.handle) : nearest(p, 28);
		const added = index < 0;
		if (added) {
			if (points.length >= 4) return;
			index = points.length;
			commit([...points, p]);
		} else {
			history = [...history.slice(-49), points];
		}
		e.preventDefault();
		surface.setPointerCapture(e.pointerId);
		const r = surface.getBoundingClientRect();
		box = { w: r.width, h: r.height };
		drag = { index, pointerId: e.pointerId, moved: false, added };
	}

	function onpointermove(e: PointerEvent) {
		if (!drag || e.pointerId !== drag.pointerId) return;
		e.preventDefault();
		const p = toNorm(e);
		const copy = points.slice();
		copy[drag.index] = p;
		drag.moved = true;
		onchange(copy);
	}

	function endDrag(e: PointerEvent) {
		if (!drag || e.pointerId !== drag.pointerId) return;
		if (surface?.hasPointerCapture(e.pointerId)) surface.releasePointerCapture(e.pointerId);
		// A tap on an existing point without moving is not an edit.
		if (!drag.moved && !drag.added) history = history.slice(0, -1);
		drag = null;
	}

	async function focusHandle(i: number) {
		await tick();
		surface?.querySelector<HTMLElement>(`[data-handle="${i}"]`)?.focus();
	}

	function onsurfacekeydown(e: KeyboardEvent) {
		if (e.target !== surface || disabled || !loaded) return;
		if ((e.key === 'Enter' || e.key === ' ') && points.length < 4) {
			e.preventDefault();
			const i = points.length;
			commit([...points, KEYBOARD_DEFAULTS[i]]);
			focusHandle(i);
		}
	}

	function onhandlekeydown(e: KeyboardEvent, i: number) {
		if (disabled) return;
		const step = e.shiftKey ? 0.01 : 0.002;
		const d: Record<string, Pt> = {
			ArrowLeft: [-step, 0],
			ArrowRight: [step, 0],
			ArrowUp: [0, -step],
			ArrowDown: [0, step]
		};
		const delta = d[e.key];
		if (!delta) return;
		e.preventDefault();
		const copy = points.slice();
		copy[i] = [clamp01(points[i][0] + delta[0]), clamp01(points[i][1] + delta[1])];
		commit(copy);
	}

	function undo() {
		if (!history.length) return;
		const prev = history[history.length - 1];
		history = history.slice(0, -1);
		onchange(prev);
	}

	function reset() {
		if (!points.length) return;
		commit([]);
	}

	const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
</script>

<div class="flex flex-col gap-4 lg:flex-row lg:items-start">
	<div class="flex flex-col gap-3 lg:order-2 lg:w-80 lg:shrink-0">
		<div class="rounded-xl border bg-card p-3">
			<LetterBlockGuide active={next} done={points.length} />
			<p class="mt-2 text-sm font-semibold text-sky-800" data-testid="position-rule">
				แตะตามตำแหน่งช่อง ไม่ใช่ตามตัวอักษรที่เห็น
			</p>
			<p class="mt-1 text-xs text-muted-foreground">
				ถ้าปุ่มถูกสลับ ให้แตะช่องที่ควรเป็น Q, P, M, Z ตามตำแหน่ง แม้ตัวอักษรบนปุ่มจะเป็นตัวอื่น
			</p>
		</div>
		<div aria-live="polite" class="text-sm" data-testid="picker-instruction">
			{#if next >= 0}
				<p>
					<span class="font-semibold">จุดที่ {next + 1}/4:</span> แตะกึ่งกลางช่อง
					<strong>{REFERENCE_SLOTS[next].expected_label}</strong> — {POSITION_TEXT[next]}
				</p>
			{:else if error}
				<p role="alert" class="font-medium text-red-700" data-testid="quad-error">
					{QUAD_ERROR_TEXT[error]}
				</p>
			{:else}
				<p class="text-emerald-800">
					ครบ 4 จุดแล้ว ลากจุดเพื่อปรับให้ตรงกึ่งกลางปุ่มได้ แล้วกดส่งตรวจ
				</p>
			{/if}
		</div>
		<div class="flex gap-2">
			<Button
				variant="outline"
				onclick={undo}
				disabled={disabled || history.length === 0}
				aria-label="ย้อนกลับหนึ่งขั้น"
			>
				<Undo2Icon /> ย้อนกลับ
			</Button>
			<Button variant="outline" onclick={reset} disabled={disabled || points.length === 0}>
				<RotateCcwIcon /> ล้างจุดทั้งหมด
			</Button>
		</div>
	</div>

	<div class="flex min-w-0 flex-1 justify-center lg:order-1">
		<!-- Custom 2D pointer surface; keyboard users press Enter here, then nudge points with arrows. -->
		<!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
		<div
			bind:this={surface}
			class="relative inline-block max-w-full touch-none overscroll-contain select-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
			style:-webkit-touch-callout="none"
			role="application"
			aria-label="ภาพสำหรับแตะจุดอ้างอิง กด Enter เพื่อวางจุดถัดไป แล้วใช้ลูกศรเลื่อนจุด"
			tabindex="0"
			data-testid="corner-surface"
			{onpointerdown}
			{onpointermove}
			onpointerup={endDrag}
			onpointercancel={endDrag}
			onkeydown={onsurfacekeydown}
		>
			<img
				src={imageUrl}
				alt="ภาพคีย์บอร์ดที่อัปโหลด"
				class="block max-h-[65svh] w-auto max-w-full rounded-lg"
				draggable="false"
				onload={() => (loaded = true)}
				onerror={() => onimageerror?.()}
			/>
			{#if loaded}
				<svg
					class="pointer-events-none absolute inset-0 h-full w-full"
					viewBox="0 0 1000 1000"
					preserveAspectRatio="none"
					aria-hidden="true"
				>
					{#if points.length >= 2}
						<polyline
							points={[...points, ...(points.length === 4 ? [points[0]] : [])]
								.map(([x, y]) => `${x * 1000},${y * 1000}`)
								.join(' ')}
							fill={points.length === 4 && !error ? 'rgb(14 165 233 / 0.12)' : 'none'}
							stroke={error ? '#dc2626' : '#0284c7'}
							stroke-width="2.5"
							stroke-dasharray={error ? '8 6' : undefined}
							vector-effect="non-scaling-stroke"
						/>
					{/if}
				</svg>
				{#each points as [x, y], i (i)}
					<button
						type="button"
						data-handle={i}
						class="absolute z-10 flex size-11 -translate-x-1/2 -translate-y-1/2 cursor-grab touch-none items-center justify-center rounded-full focus-visible:ring-[3px] focus-visible:ring-sky-400 focus-visible:outline-none"
						style:left={pct(x)}
						style:top={pct(y)}
						aria-label="จุดที่ {i + 1} ช่อง {REFERENCE_SLOTS[i].expected_label} ที่ {pct(x)}, {pct(
							y
						)} — ใช้ปุ่มลูกศรเพื่อเลื่อน (Shift เลื่อนมากขึ้น)"
						onkeydown={(e) => onhandlekeydown(e, i)}
						{disabled}
					>
						<span
							class="pointer-events-none block size-5 rounded-full border-2 border-white bg-sky-600/40 shadow-[0_0_0_2px_rgb(2_132_199)]"
						></span>
						<span
							class="pointer-events-none absolute top-1/2 left-1/2 size-1 -translate-1/2 rounded-full bg-white"
						></span>
						<span
							class="pointer-events-none absolute -top-3 left-8 rounded bg-sky-700 px-1.5 py-0.5 text-xs font-bold whitespace-nowrap text-white"
							>{i + 1} · {REFERENCE_SLOTS[i].expected_label}</span
						>
					</button>
				{/each}
				{#if loupe}
					<div
						class={[
							'pointer-events-none absolute top-2 z-20 overflow-hidden rounded-full border-4 border-white shadow-lg',
							loupe.side === 'right' ? 'right-2' : 'left-2'
						]}
						style:width="{LOUPE}px"
						style:height="{LOUPE}px"
						style:background-image="url({JSON.stringify(imageUrl)})"
						style:background-size={loupe.bgSize}
						style:background-position={loupe.bgPos}
						style:background-repeat="no-repeat"
						aria-hidden="true"
					>
						<span class="absolute top-1/2 left-0 h-px w-full bg-sky-500"></span>
						<span class="absolute top-0 left-1/2 h-full w-px bg-sky-500"></span>
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>
