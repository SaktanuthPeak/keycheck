<script lang="ts">
	import { resolve } from '$app/paths';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { useQueryClient } from '@tanstack/svelte-query';
	import { toast } from 'svelte-sonner';
	import LoaderCircleIcon from '@lucide/svelte/icons/loader-circle';
	import SendIcon from '@lucide/svelte/icons/send';
	import RotateCcwIcon from '@lucide/svelte/icons/rotate-ccw';
	import { Button } from '$lib/components/ui/button';
	import {
		CornerPicker,
		Flow,
		inspectionApi,
		inspectionKeys,
		Notice,
		useCreateInspection,
		useLayouts,
		validateQuad,
		type Pt,
		type Quad,
		type Upload
	} from '$lib/features/inspection';
	import { uuid } from '$lib/utils/uuid';

	const flow = new Flow('calibrating');
	const queryClient = useQueryClient();
	const layouts = useLayouts();
	const create = useCreateInspection();

	const imageId = $derived(page.url.searchParams.get('image') ?? '');
	const cached = $derived(
		imageId ? queryClient.getQueryData<Upload>(inspectionKeys.upload(imageId)) : undefined
	);
	const imageUrl = $derived(imageId ? (cached?.image_url ?? inspectionApi.imageUrl(imageId)) : '');
	const layout = $derived(layouts.data?.[0]);

	let points = $state.raw<Pt[]>([]);
	let imageFailed = $state(false);
	// Set synchronously on click so a double tap cannot fire two requests before isPending updates.
	let submitting = $state(false);
	let submitError = $state<{ message: string; retryable: boolean } | null>(null);
	// One id per submit attempt: reused by automatic and manual retries, reset when points change.
	let clientRequestId: string | null = null;

	const quadError = $derived(points.length === 4 ? validateQuad(points) : null);
	const canSubmit = $derived(
		points.length === 4 &&
			!quadError &&
			!!layout &&
			!submitting &&
			!create.isPending &&
			!imageFailed
	);

	function onchange(next: Pt[]) {
		points = next;
		clientRequestId = null;
		submitError = null;
	}

	function submit() {
		if (!canSubmit || !layout) return;
		clientRequestId ??= uuid();
		submitError = null;
		submitting = true;
		create.mutate(
			{
				image_id: imageId,
				layout_id: layout.layout_id,
				reference_points_normalized: points as unknown as Quad,
				client_request_id: clientRequestId
			},
			{
				onSuccess: (res) => {
					flow.send('SUBMITTED');
					goto(resolve('/inspections/[id]', { id: res.inspection_id }));
				},
				onError: (e) => {
					submitting = false;
					submitError = { message: e.message, retryable: e.retryable };
					if (!e.retryable) clientRequestId = null;
					if (e.code === 'IMAGE_EXPIRED' || e.code === 'NOT_FOUND') imageFailed = true;
					toast.error(e.message);
				}
			}
		);
	}

	function retake() {
		flow.send('RETAKE');
		goto(resolve('/'));
	}
</script>

<div class="flex flex-col gap-4" data-flow-state={flow.state}>
	<div class="flex flex-col gap-1">
		<h1 class="text-2xl font-bold">แตะจุดอ้างอิง 4 จุด</h1>
		<p class="text-sm text-muted-foreground">
			แตะกึ่งกลางช่อง Q → P → M → Z ตามลำดับ เพื่อให้ระบบจัดภาพคีย์บอร์ดให้ตรงก่อนตรวจ
		</p>
	</div>

	{#if !imageId}
		<Notice tone="error" role="alert" title="ไม่พบภาพที่จะตรวจ">
			<p>กรุณาเริ่มจากการถ่ายหรือเลือกภาพใหม่</p>
			{#snippet actions()}<Button href={resolve('/')}>ถ่ายภาพ</Button>{/snippet}
		</Notice>
	{:else if imageFailed || !imageUrl}
		<Notice tone="error" role="alert" title="เปิดภาพนี้ไม่ได้" testid="image-expired">
			<p>
				ภาพอาจหมดอายุและถูกลบตามระยะเวลาเก็บรักษาแล้ว หรือไม่ใช่ภาพของอุปกรณ์นี้ กรุณาถ่ายภาพใหม่
			</p>
			{#snippet actions()}<Button href={resolve('/')}>ถ่ายภาพใหม่</Button>{/snippet}
		</Notice>
	{:else}
		{#key imageId}
			<CornerPicker
				{imageUrl}
				{points}
				{onchange}
				disabled={submitting}
				onimageerror={() => (imageFailed = true)}
			/>
		{/key}

		{#if layouts.isError}
			<Notice tone="error" role="alert" title="โหลดข้อมูลรูปแบบคีย์บอร์ดไม่ได้">
				{#snippet actions()}
					<Button variant="outline" size="sm" onclick={() => layouts.refetch()}>ลองใหม่</Button>
				{/snippet}
			</Notice>
		{/if}

		{#if submitError}
			<Notice tone="error" role="alert" testid="submit-error">
				<p>{submitError.message}</p>
				{#snippet actions()}
					{#if submitError?.retryable}
						<Button size="sm" onclick={submit} disabled={!canSubmit}>ลองส่งอีกครั้ง</Button>
					{/if}
				{/snippet}
			</Notice>
		{/if}

		<div
			class="sticky bottom-0 z-20 -mx-4 grid gap-2 border-t bg-background/95 px-4 py-3 backdrop-blur sm:static sm:mx-0 sm:grid-cols-2 sm:border-0 sm:bg-transparent sm:p-0"
		>
			<Button variant="outline" class="h-12 text-base" onclick={retake} disabled={submitting}>
				<RotateCcwIcon class="size-5" /> ถ่ายใหม่
			</Button>
			<Button class="h-12 text-base" onclick={submit} disabled={!canSubmit}>
				{#if submitting}
					<LoaderCircleIcon class="size-5 animate-spin" /> กำลังส่งตรวจ…
				{:else}
					<SendIcon class="size-5" /> ส่งตรวจ
				{/if}
			</Button>
		</div>
	{/if}
</div>
