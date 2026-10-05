<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';
	import CameraIcon from '@lucide/svelte/icons/camera';
	import CrosshairIcon from '@lucide/svelte/icons/crosshair';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import WifiOffIcon from '@lucide/svelte/icons/wifi-off';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import {
		errorMessage,
		formatDateTime,
		inspectionApi,
		Notice,
		ResultOverlay,
		ResultSummary,
		SlotList,
		StageProgress,
		stateFromStatus,
		STATUS_TEXT,
		useCreateInspection,
		useInspection
	} from '$lib/features/inspection';
	import { uuid } from '$lib/utils/uuid';

	const id = $derived(page.params.id ?? '');
	const query = useInspection(() => id);
	const resubmit = useCreateInspection();

	const ins = $derived(query.data);
	const flowState = $derived(ins ? stateFromStatus(ins.status) : null);
	const recalibrateHref = $derived(
		ins && !ins.image_expired
			? `${resolve('/inspect')}?image=${encodeURIComponent(ins.image_id)}`
			: null
	);
	const pollProblem = $derived(
		!!ins && query.isError && !['completed', 'rejected', 'failed'].includes(ins.status)
	);

	let selected = $state<string | null>(null);
	let resubmitId: string | null = null;

	function resubmitJob() {
		if (!ins || resubmit.isPending) return;
		// A deliberate new job for the same image/points; its retries reuse this id.
		resubmitId ??= uuid();
		resubmit.mutate(
			{
				image_id: ins.image_id,
				layout_id: ins.layout_id,
				reference_points_normalized: ins.reference_points_normalized,
				client_request_id: resubmitId
			},
			{
				onSuccess: (r) => {
					resubmitId = null;
					goto(resolve('/inspections/[id]', { id: r.inspection_id }));
				},
				onError: (e) => {
					if (!e.retryable) resubmitId = null;
					toast.error(e.message);
				}
			}
		);
	}
</script>

{#snippet retakeButtons(primaryRecalibrate: boolean)}
	{#if recalibrateHref}
		<Button href={recalibrateHref} variant={primaryRecalibrate ? 'default' : 'outline'}>
			<CrosshairIcon /> แตะจุดอ้างอิงใหม่
		</Button>
	{/if}
	<Button
		href={resolve('/')}
		variant={primaryRecalibrate && recalibrateHref ? 'outline' : 'default'}
	>
		<CameraIcon /> ถ่ายตรวจใหม่
	</Button>
{/snippet}

<div class="flex flex-col gap-5" data-flow-state={flowState ?? 'loading'}>
	{#if !ins}
		{#if query.isError}
			<Notice
				tone="error"
				role="alert"
				title={query.error?.code === 'NOT_FOUND' ? 'ไม่พบงานตรวจนี้' : 'โหลดสถานะงานไม่ได้'}
				testid="load-error"
			>
				<p>{query.error?.message}</p>
				{#snippet actions()}
					{#if query.error?.retryable}
						<Button size="sm" variant="outline" onclick={() => query.refetch()}>
							<RefreshCwIcon /> ลองใหม่
						</Button>
					{/if}
					<Button size="sm" href={resolve('/')}>ถ่ายตรวจใหม่</Button>
				{/snippet}
			</Notice>
		{:else}
			<div class="flex flex-col gap-3" aria-busy="true">
				<p class="text-muted-foreground">กำลังโหลดสถานะงาน…</p>
				<Skeleton class="h-8 w-1/2" />
				<Skeleton class="h-48 w-full" />
			</div>
		{/if}
	{:else}
		{#if pollProblem}
			<Notice tone="warning" role="status" testid="poll-error">
				<p class="flex items-center gap-2">
					<WifiOffIcon class="size-4" aria-hidden="true" />
					การเชื่อมต่อขาดช่วง กำลังลองใหม่อัตโนมัติ — งานยังทำต่อที่เซิร์ฟเวอร์
				</p>
				{#snippet actions()}
					<Button size="sm" variant="outline" onclick={() => query.refetch()}>
						<RefreshCwIcon /> ลองตอนนี้
					</Button>
				{/snippet}
			</Notice>
		{/if}

		{#if ins.status === 'queued' || ins.status === 'processing'}
			<section class="flex flex-col gap-3 rounded-xl border bg-card p-4" aria-busy="true">
				<StageProgress status={ins.status} stage={ins.stage} />
				<p class="text-sm text-muted-foreground">
					หน้านี้อัปเดตเองอัตโนมัติ ไม่ต้องรีเฟรช ถ้าออกจากหน้านี้ กลับมาดูผลได้จากเมนู "ประวัติ"
				</p>
			</section>
		{:else if ins.status === 'completed'}
			<ResultSummary inspection={ins} simulated={inspectionApi.simulated} />

			{#if ins.image_expired}
				<Notice tone="warning" title="ภาพของงานนี้หมดอายุแล้ว" testid="image-expired">
					<p>
						ภาพถูกลบตามระยะเวลาเก็บรักษา จึงแสดงได้เฉพาะกรอบตำแหน่งและผลรายช่อง หากต้องการดูบนภาพ
						กรุณาถ่ายตรวจใหม่
					</p>
				</Notice>
			{/if}

			<div class="grid gap-5 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
				<section class="flex flex-col gap-2" aria-label="ภาพผลตรวจ">
					<ResultOverlay
						imageUrl={ins.image_url}
						width={ins.image_width}
						height={ins.image_height}
						slots={ins.slots}
						selectedId={selected}
						expired={ins.image_expired}
						onselect={(sid) => (selected = selected === sid ? null : sid)}
					/>
					<p class="text-xs text-muted-foreground">
						สัญลักษณ์: ✓ เขียว = ถูก · ! แดง = ผิด · ? เหลือง = ไม่แน่ใจ · เส้นประ = กรอบตามแบบ
						(ไม่ได้ตรวจจับปุ่มจริง) — แตะรายการหรือกรอบเพื่อเน้นช่อง
					</p>
				</section>
				<section class="flex flex-col gap-2" aria-label="ผลรายช่อง">
					<h3 class="font-semibold">ผลรายช่อง</h3>
					<SlotList slots={ins.slots} selectedId={selected} onselect={(sid) => (selected = sid)} />
				</section>
			</div>

			<div class="flex flex-wrap gap-2">{@render retakeButtons(false)}</div>
		{:else if ins.status === 'rejected'}
			<Notice tone="error" role="alert" title="ตรวจภาพนี้ไม่ได้" testid="rejected">
				<p>{errorMessage(ins.error?.code ?? 'INTERNAL_ERROR', ins.error?.message)}</p>
				{#if ins.error?.code === 'LAYOUT_MISMATCH'}
					<ul class="mt-1 list-disc pl-5">
						<li>
							ตรวจว่าแตะกึ่งกลางช่อง Q, P, M, Z ตามตำแหน่งจริง ไม่เลื่อนไปช่องข้าง ๆ แล้วลองใหม่
						</li>
						<li>ถ้าแตะถูกแล้วยังไม่ผ่าน คีย์บอร์ดรุ่นนี้อาจไม่ใช่แถวเยื้องมาตรฐานที่ระบบรองรับ</li>
					</ul>
				{/if}
				{#snippet actions()}{@render retakeButtons(true)}{/snippet}
			</Notice>
		{:else}
			<Notice tone="error" role="alert" title={STATUS_TEXT.failed} testid="failed">
				<p>{errorMessage(ins.error?.code ?? 'PROCESSING_FAILED', ins.error?.message)}</p>
				{#snippet actions()}
					{#if ins.error?.retryable && !ins.image_expired}
						<Button onclick={resubmitJob} disabled={resubmit.isPending}>
							<RefreshCwIcon /> ส่งตรวจอีกครั้ง
						</Button>
					{/if}
					{@render retakeButtons(false)}
				{/snippet}
			</Notice>
		{/if}

		<details class="text-xs text-muted-foreground">
			<summary class="cursor-pointer">ข้อมูลสำหรับตรวจสอบ</summary>
			<dl class="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
				<dt>รหัสงาน</dt>
				<dd class="break-all">{ins.inspection_id}</dd>
				<dt>สถานะ</dt>
				<dd>{STATUS_TEXT[ins.status]}</dd>
				<dt>ส่งเมื่อ</dt>
				<dd>{formatDateTime(ins.created_at)}</dd>
				<dt>เสร็จเมื่อ</dt>
				<dd>{formatDateTime(ins.finished_at)}</dd>
				<dt>Layout</dt>
				<dd>{ins.layout_id} v{ins.layout_version}</dd>
				<dt>Model bundle</dt>
				<dd>{ins.model_bundle_id ?? '-'}</dd>
			</dl>
		</details>
	{/if}
</div>
