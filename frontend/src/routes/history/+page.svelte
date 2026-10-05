<script lang="ts">
	import { resolve } from '$app/paths';
	import ChevronRightIcon from '@lucide/svelte/icons/chevron-right';
	import RefreshCwIcon from '@lucide/svelte/icons/refresh-cw';
	import { Button } from '$lib/components/ui/button';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import {
		errorMessage,
		formatDateTime,
		Notice,
		STATUS_TEXT,
		useInspectionHistory,
		type ApiError,
		type InspectionStatus
	} from '$lib/features/inspection';

	const history = useInspectionHistory();
	const items = $derived(history.data?.pages.flatMap((p) => p.items) ?? []);
	const err = $derived(history.error as ApiError | null);

	const TONE: Record<InspectionStatus, string> = {
		queued: 'border-sky-300 bg-sky-50 text-sky-900',
		processing: 'border-sky-300 bg-sky-50 text-sky-900',
		completed: 'border-emerald-300 bg-emerald-50 text-emerald-900',
		rejected: 'border-red-300 bg-red-50 text-red-900',
		failed: 'border-red-300 bg-red-50 text-red-900'
	};
</script>

<div class="flex flex-col gap-4">
	<div class="flex flex-col gap-1">
		<h1 class="text-2xl font-bold">ประวัติการตรวจ</h1>
		<p class="text-sm text-muted-foreground">
			งานตรวจล่าสุดของเบราว์เซอร์นี้ ภาพจะถูกลบภายใน 24 ชั่วโมง ส่วนผลตรวจเก็บไว้ 7 วัน
		</p>
	</div>

	{#if history.isPending}
		<div class="flex flex-col gap-2" aria-busy="true">
			<Skeleton class="h-16 w-full" />
			<Skeleton class="h-16 w-full" />
		</div>
	{:else if history.isError && !items.length}
		<Notice tone="error" role="alert" title="โหลดประวัติไม่ได้">
			<p>
				{err?.status === 404 || err?.status === 405
					? 'เซิร์ฟเวอร์นี้ยังไม่เปิดใช้งานประวัติการตรวจ'
					: errorMessage(err?.code ?? 'INTERNAL_ERROR')}
			</p>
			{#snippet actions()}
				<Button size="sm" variant="outline" onclick={() => history.refetch()}>
					<RefreshCwIcon /> ลองใหม่
				</Button>
			{/snippet}
		</Notice>
	{:else if !items.length}
		<Notice tone="info" title="ยังไม่มีประวัติการตรวจ">
			{#snippet actions()}<Button href={resolve('/')}>เริ่มตรวจคีย์บอร์ด</Button>{/snippet}
		</Notice>
	{:else}
		<ul class="flex flex-col gap-2" data-testid="history-list">
			{#each items as item (item.inspection_id)}
				<li>
					<a
						href={resolve('/inspections/[id]', { id: item.inspection_id })}
						class="flex items-center gap-3 rounded-lg border bg-card p-3 transition-colors hover:bg-muted/50 focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none"
					>
						<div class="flex min-w-0 flex-1 flex-col gap-1">
							<div class="flex flex-wrap items-center gap-2">
								<span class={['rounded-full border px-2 py-0.5 text-xs', TONE[item.status]]}>
									{STATUS_TEXT[item.status]}
								</span>
								<span class="text-sm text-muted-foreground">{formatDateTime(item.created_at)}</span>
								{#if item.image_expired}
									<span class="text-xs text-muted-foreground">(ภาพหมดอายุแล้ว)</span>
								{/if}
							</div>
							{#if item.summary}
								<p class="text-sm">
									ถูก {item.summary.correct} · ผิด {item.summary.incorrect} · ไม่แน่ใจ
									{item.summary.uncertain}
								</p>
							{:else if item.error}
								<p class="text-sm text-red-800">
									{errorMessage(item.error.code, item.error.message)}
								</p>
							{/if}
						</div>
						<ChevronRightIcon class="size-5 shrink-0 text-muted-foreground" aria-hidden="true" />
					</a>
				</li>
			{/each}
		</ul>
		{#if history.hasNextPage}
			<Button
				variant="outline"
				onclick={() => history.fetchNextPage()}
				disabled={history.isFetchingNextPage}
			>
				โหลดเพิ่ม
			</Button>
		{/if}
	{/if}
</div>
