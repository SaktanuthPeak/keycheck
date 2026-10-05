<script lang="ts">
	import { resolve } from '$app/paths';
	import { onDestroy } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	import CheckIcon from '@lucide/svelte/icons/check';
	import XIcon from '@lucide/svelte/icons/x';
	import UploadIcon from '@lucide/svelte/icons/upload';
	import RotateCcwIcon from '@lucide/svelte/icons/rotate-ccw';
	import LoaderCircleIcon from '@lucide/svelte/icons/loader-circle';
	import { Button } from '$lib/components/ui/button';
	import {
		Camera,
		checkLocalFile,
		Flow,
		LetterBlockGuide,
		Notice,
		useLayouts,
		useUploadImage
	} from '$lib/features/inspection';

	const flow = new Flow('idle');
	const layouts = useLayouts();
	const upload = useUploadImage();

	let file = $state.raw<File | null>(null);
	let previewUrl = $state<string | null>(null);
	let previewSize = $state<{ w: number; h: number } | null>(null);
	let fileError = $state<string | null>(null);
	let uploadError = $state<string | null>(null);

	const layout = $derived(layouts.data?.[0]);
	const lowRes = $derived(!!previewSize && previewSize.w * previewSize.h < 1_000_000);

	function clearPreview() {
		if (previewUrl) URL.revokeObjectURL(previewUrl);
		previewUrl = null;
		previewSize = null;
		file = null;
	}

	function select(f: File) {
		uploadError = null;
		const err = checkLocalFile(f);
		if (err) {
			fileError = err;
			toast.error(err);
			if (flow.is('camera_permission')) flow.send('CLOSE_CAMERA');
			return;
		}
		fileError = null;
		clearPreview();
		file = f;
		previewUrl = URL.createObjectURL(f);
		flow.send('IMAGE_SELECTED');
	}

	function retake() {
		clearPreview();
		uploadError = null;
		flow.send('RETAKE');
	}

	function startUpload() {
		if (!file || upload.isPending) return;
		uploadError = null;
		flow.send('UPLOAD');
		upload.mutate(file, {
			onSuccess: (u) => {
				flow.send('UPLOADED');
				// eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved path + query string
				goto(`${resolve('/inspect')}?image=${encodeURIComponent(u.image_id)}`);
			},
			onError: (e) => {
				flow.send('UPLOAD_FAILED');
				uploadError = e.message;
				toast.error(e.message);
			}
		});
	}

	onDestroy(clearPreview);
</script>

<div class="flex flex-col gap-6" data-flow-state={flow.state}>
	<section class="flex flex-col gap-2">
		<h1 class="text-2xl font-bold sm:text-3xl">ตรวจตำแหน่งคีย์แคป A–Z</h1>
		<p class="text-muted-foreground">
			ตรวจคีย์แคป A–Z บนคีย์บอร์ด QWERTY แถวเยื้องทั่วไป (อ่านเฉพาะตัวอักษรอังกฤษ)
		</p>
		<p class="text-sm" data-testid="layout-name">
			รูปแบบที่ตรวจ:
			{#if layout}
				<strong>{layout.name}</strong>
				<span class="text-muted-foreground">({layout.supported_form_factors.join(' / ')})</span>
			{:else if layouts.isError}
				<span class="text-red-700">โหลดข้อมูลรูปแบบคีย์บอร์ดไม่ได้</span>
				<Button variant="link" class="h-auto p-0" onclick={() => layouts.refetch()}>ลองใหม่</Button>
			{:else}
				<span class="text-muted-foreground">กำลังโหลด…</span>
			{/if}
		</p>
	</section>

	{#if flow.is('idle', 'camera_permission')}
		<section class="grid gap-6 md:grid-cols-2">
			<div class="flex flex-col gap-4 rounded-xl border bg-card p-4">
				<h2 class="font-semibold">ถ่ายหรือเลือกภาพคีย์บอร์ด</h2>
				<Camera
					onselect={select}
					onopen={() => flow.send('OPEN_CAMERA')}
					onclose={() => flow.send('CLOSE_CAMERA')}
				/>
				{#if fileError}
					<Notice tone="error" role="alert" testid="file-error"><p>{fileError}</p></Notice>
				{/if}
				<p class="text-xs text-muted-foreground">
					รองรับ JPEG / PNG ขนาดไม่เกิน 15 MiB ภาพจะถูกส่งด้วยความละเอียดเต็ม และลบอัตโนมัติภายใน 24
					ชั่วโมง
				</p>
			</div>

			{#if flow.is('idle')}
				<div class="flex flex-col gap-4">
					<div class="rounded-xl border p-4">
						<h2 class="mb-2 font-semibold">วิธีถ่าย</h2>
						<ol class="list-decimal space-y-1 pl-5 text-sm">
							<li>ถ่ายจากด้านบนให้ตั้งฉากกับคีย์บอร์ดมากที่สุด เห็นปุ่ม A–Z ครบทุกปุ่ม</li>
							<li>ใช้แสงสม่ำเสมอ หลีกเลี่ยงเงา แสงสะท้อน และมือหรือสิ่งของบังปุ่ม</li>
							<li>ถือกล้องให้นิ่ง ไม่ซูมแบบดิจิทัล ให้บล็อกตัวอักษรเต็มภาพพอสมควร</li>
							<li>ถัดไปจะให้แตะกึ่งกลางช่อง Q, P, M, Z ตามตำแหน่ง เพื่อจัดภาพให้ตรง</li>
						</ol>
						<div class="mt-3 flex justify-center"><LetterBlockGuide /></div>
					</div>
					<div class="rounded-xl border p-4 text-sm">
						<h2 class="mb-2 font-semibold">ขอบเขตที่รองรับ</h2>
						<ul class="space-y-1">
							<li class="flex gap-2">
								<CheckIcon class="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
								คีย์บอร์ด QWERTY แถวเยื้องมาตรฐาน แบบ ANSI และ ISO
							</li>
							<li class="flex gap-2">
								<CheckIcon class="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
								ปุ่มไทย-อังกฤษใช้ได้ ระบบอ่านเฉพาะตัวอักษรอังกฤษ
							</li>
							<li class="flex gap-2">
								<CheckIcon class="mt-0.5 size-4 shrink-0 text-emerald-600" aria-hidden="true" />
								ตรวจเฉพาะ 26 ปุ่ม A–Z
							</li>
							<li class="flex gap-2">
								<XIcon class="mt-0.5 size-4 shrink-0 text-red-600" aria-hidden="true" />
								ไม่ตรวจตัวเลข สัญลักษณ์ และปุ่มฟังก์ชัน
							</li>
							<li class="flex gap-2">
								<XIcon class="mt-0.5 size-4 shrink-0 text-red-600" aria-hidden="true" />
								ไม่รองรับคีย์บอร์ด Ortholinear, Split และผังอื่นเช่น AZERTY / QWERTZ
							</li>
						</ul>
					</div>
				</div>
			{/if}
		</section>
	{:else if previewUrl}
		<section class="flex flex-col gap-4" aria-labelledby="preview-heading">
			<h2 id="preview-heading" class="font-semibold">ตรวจดูภาพก่อนส่ง</h2>
			<div class="flex justify-center rounded-xl border bg-muted/40 p-2">
				<img
					src={previewUrl}
					alt="ภาพตัวอย่างก่อนอัปโหลด"
					class="max-h-[60svh] w-auto max-w-full rounded-lg"
					data-testid="local-preview"
					onload={(e) => {
						const img = e.currentTarget as HTMLImageElement;
						previewSize = { w: img.naturalWidth, h: img.naturalHeight };
					}}
				/>
			</div>
			{#if previewSize}
				<p class="text-center text-xs text-muted-foreground">
					{previewSize.w} × {previewSize.h} พิกเซล
				</p>
			{/if}
			{#if lowRes}
				<Notice tone="warning"
					><p>
						ภาพความละเอียดต่ำ ตัวอักษรอาจอ่านไม่ชัด แนะนำให้ถ่ายใหม่ใกล้ขึ้นหรือใช้ภาพต้นฉบับ
					</p></Notice
				>
			{/if}
			<p class="text-sm text-muted-foreground">
				เห็นปุ่ม A–Z ครบ ไม่เบลอ และไม่มีแสงสะท้อนบังตัวอักษรหรือไม่? ถ้าไม่ชัดให้ถ่ายใหม่
			</p>
			{#if uploadError}
				<Notice tone="error" role="alert" testid="upload-error">
					<p>{uploadError}</p>
				</Notice>
			{/if}
			<div class="grid gap-2 sm:grid-cols-2">
				<Button
					variant="outline"
					class="h-12 text-base"
					onclick={retake}
					disabled={flow.is('uploading')}
				>
					<RotateCcwIcon class="size-5" /> ถ่ายใหม่ / เลือกภาพอื่น
				</Button>
				<Button class="h-12 text-base" onclick={startUpload} disabled={flow.is('uploading')}>
					{#if flow.is('uploading')}
						<LoaderCircleIcon class="size-5 animate-spin" /> กำลังอัปโหลด…
					{:else}
						<UploadIcon class="size-5" /> {uploadError ? 'ลองอัปโหลดอีกครั้ง' : 'ใช้ภาพนี้'}
					{/if}
				</Button>
			</div>
		</section>
	{/if}
</div>
