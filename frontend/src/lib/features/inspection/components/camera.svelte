<!--
	Camera capture (Spec §10.3). Live getUserMedia (rear camera, full resolution) when available;
	file inputs are always offered and become the main path when permission is denied, there are no
	MediaDevices, or the page is not a secure context. Media tracks stop on capture and on destroy.
-->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import CameraIcon from '@lucide/svelte/icons/camera';
	import ImageIcon from '@lucide/svelte/icons/image';
	import XIcon from '@lucide/svelte/icons/x';
	import { Button, buttonVariants } from '$lib/components/ui/button';
	import { cn } from '$lib/utils/shadcn';

	type Props = {
		/** Called with a captured photo or a chosen file. */
		onselect: (file: File) => void;
		/** Camera flow started (permission prompt / viewfinder). */
		onopen?: () => void;
		/** Camera flow ended without a photo (cancel, denied, unsupported, error). */
		onclose?: () => void;
		disabled?: boolean;
	};

	let { onselect, onopen, onclose, disabled = false }: Props = $props();

	type CamState = 'off' | 'requesting' | 'live' | 'denied' | 'unavailable' | 'error';

	const supported =
		typeof window !== 'undefined' &&
		window.isSecureContext &&
		!!navigator.mediaDevices?.getUserMedia;
	const coarsePointer =
		typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches;

	let camState = $state<CamState>(supported ? 'off' : 'unavailable');
	let stream = $state.raw<MediaStream | null>(null);
	let video = $state<HTMLVideoElement | null>(null);
	let capturing = $state(false);

	const cameraBlocked = $derived(camState === 'denied' || camState === 'unavailable');
	const showCaptureInput = $derived(coarsePointer || cameraBlocked || camState === 'error');

	function stopTracks(s: MediaStream | null) {
		s?.getTracks().forEach((t) => t.stop());
	}

	function stop() {
		stopTracks(stream);
		stream = null;
	}

	async function open() {
		if (!supported) {
			camState = 'unavailable';
			return;
		}
		camState = 'requesting';
		onopen?.();
		try {
			const s = await navigator.mediaDevices.getUserMedia({
				audio: false,
				video: {
					facingMode: { ideal: 'environment' },
					width: { ideal: 4096 },
					height: { ideal: 3072 }
				}
			});
			if (camState !== 'requesting') {
				stopTracks(s);
				return;
			}
			stream = s;
			camState = 'live';
		} catch (e) {
			const name = e instanceof DOMException ? e.name : '';
			camState =
				name === 'NotAllowedError' || name === 'SecurityError'
					? 'denied'
					: name === 'NotFoundError' || name === 'OverconstrainedError'
						? 'unavailable'
						: 'error';
			onclose?.();
		}
	}

	function cancel() {
		stop();
		camState = 'off';
		onclose?.();
	}

	type ImageCaptureLike = { takePhoto(): Promise<Blob> };
	type ImageCaptureCtor = new (track: MediaStreamTrack) => ImageCaptureLike;

	async function grabFrame(): Promise<Blob | null> {
		const track = stream?.getVideoTracks()[0];
		const IC = (window as unknown as { ImageCapture?: ImageCaptureCtor }).ImageCapture;
		if (track && IC) {
			try {
				// Full sensor resolution where supported (Chrome on Android).
				return await new IC(track).takePhoto();
			} catch {
				// fall back to the video frame
			}
		}
		if (!video || !video.videoWidth) return null;
		const canvas = document.createElement('canvas');
		canvas.width = video.videoWidth;
		canvas.height = video.videoHeight;
		canvas.getContext('2d')?.drawImage(video, 0, 0);
		return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.92));
	}

	async function capture() {
		if (capturing) return;
		capturing = true;
		try {
			const blob = await grabFrame();
			if (!blob) {
				camState = 'error';
				stop();
				onclose?.();
				return;
			}
			stop();
			camState = 'off';
			const type = blob.type || 'image/jpeg';
			const ext = type === 'image/png' ? 'png' : 'jpg';
			onselect(new File([blob], `keycheck-${Date.now()}.${ext}`, { type }));
		} finally {
			capturing = false;
		}
	}

	function onfile(e: Event & { currentTarget: HTMLInputElement }) {
		const f = e.currentTarget.files?.[0];
		e.currentTarget.value = '';
		if (f) onselect(f);
	}

	function attachStream(el: HTMLVideoElement) {
		el.srcObject = stream;
		return () => {
			el.srcObject = null;
		};
	}

	onDestroy(stop);
</script>

<div class="flex flex-col gap-3" data-camera-state={camState}>
	{#if camState === 'requesting' || camState === 'live'}
		<div class="relative overflow-hidden rounded-xl bg-black">
			<video
				bind:this={video}
				{@attach attachStream}
				class="block max-h-[70svh] w-full object-contain"
				autoplay
				playsinline
				muted
				aria-label="ภาพจากกล้อง"
			></video>
			{#if camState === 'requesting'}
				<p class="absolute inset-0 grid place-items-center p-4 text-center text-sm text-white">
					กำลังขอสิทธิ์ใช้กล้อง… กรุณากด "อนุญาต" ในเบราว์เซอร์
				</p>
			{/if}
		</div>
		<div class="flex gap-2">
			<Button
				class="h-12 flex-1 text-base"
				onclick={capture}
				disabled={camState !== 'live' || capturing}
			>
				<CameraIcon class="size-5" /> ถ่ายภาพ
			</Button>
			<Button variant="outline" class="h-12" onclick={cancel} aria-label="ปิดกล้อง">
				<XIcon class="size-5" /> ปิดกล้อง
			</Button>
		</div>
	{:else}
		{#if camState === 'denied'}
			<p
				role="alert"
				class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
			>
				ไม่ได้รับสิทธิ์ใช้กล้อง — ถ่ายด้วยแอปกล้องหรือเลือกไฟล์ภาพแทนได้
				(เปิดสิทธิ์กล้องได้ในการตั้งค่าเว็บไซต์ของเบราว์เซอร์)
			</p>
		{:else if camState === 'unavailable'}
			<p role="status" class="rounded-lg border bg-muted p-3 text-sm text-muted-foreground">
				{#if typeof window !== 'undefined' && !window.isSecureContext}
					เปิดกล้องในหน้าเว็บไม่ได้เพราะไม่ได้ใช้ HTTPS — ถ่ายด้วยแอปกล้องหรือเลือกไฟล์ภาพแทน
				{:else}
					อุปกรณ์หรือเบราว์เซอร์นี้เปิดกล้องในหน้าเว็บไม่ได้ — ถ่ายด้วยแอปกล้องหรือเลือกไฟล์ภาพแทน
				{/if}
			</p>
		{:else if camState === 'error'}
			<p
				role="alert"
				class="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900"
			>
				เปิดกล้องไม่สำเร็จ — ลองอีกครั้ง หรือถ่ายด้วยแอปกล้อง/เลือกไฟล์ภาพแทน
			</p>
		{/if}

		<div class="grid gap-2 sm:grid-cols-2">
			{#if supported && !cameraBlocked}
				<Button class="h-12 text-base" onclick={open} {disabled}>
					<CameraIcon class="size-5" /> เปิดกล้องถ่ายภาพ
				</Button>
			{/if}
			{#if showCaptureInput}
				<label
					class={cn(
						buttonVariants({ variant: cameraBlocked ? 'default' : 'outline' }),
						'h-12 cursor-pointer text-base has-[:focus-visible]:ring-[3px] has-[:focus-visible]:ring-ring/50',
						disabled && 'pointer-events-none opacity-50'
					)}
				>
					<CameraIcon class="size-5" /> ถ่ายด้วยแอปกล้อง
					<input
						class="sr-only"
						type="file"
						accept="image/*"
						capture="environment"
						onchange={onfile}
						{disabled}
					/>
				</label>
			{/if}
			<label
				class={cn(
					buttonVariants({ variant: 'outline' }),
					'h-12 cursor-pointer text-base has-[:focus-visible]:ring-[3px] has-[:focus-visible]:ring-ring/50',
					disabled && 'pointer-events-none opacity-50'
				)}
			>
				<ImageIcon class="size-5" /> เลือกไฟล์ภาพ
				<input
					class="sr-only"
					type="file"
					accept="image/jpeg,image/png,image/*"
					onchange={onfile}
					{disabled}
				/>
			</label>
		</div>
	{/if}
</div>
