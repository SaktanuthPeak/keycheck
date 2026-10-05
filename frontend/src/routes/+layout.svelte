<script lang="ts">
	import { resolve } from '$app/paths';
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { dev } from '$app/environment';
	import { page } from '$app/state';
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { SvelteQueryDevtools } from '@tanstack/svelte-query-devtools';
	import FlaskConicalIcon from '@lucide/svelte/icons/flask-conical';
	import KeyboardIcon from '@lucide/svelte/icons/keyboard';
	import { Toaster } from '$lib/components/ui/sonner/index.js';
	import { APP_TITLE, USE_MOCK } from '$lib/config';

	let { children, data } = $props();

	const NAV = [
		{
			href: resolve('/'),
			label: 'ตรวจคีย์บอร์ด',
			match: (p: string) => p === '/' || p.startsWith('/inspect')
		},
		{ href: resolve('/history'), label: 'ประวัติ', match: (p: string) => p.startsWith('/history') }
	];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>{APP_TITLE}</title>
</svelte:head>

<Toaster position="top-center" richColors closeButton />

<QueryClientProvider client={data.queryClient}>
	<div class="flex min-h-svh flex-col">
		<header class="sticky top-0 z-30 border-b bg-background/95 backdrop-blur">
			<div class="mx-auto flex h-14 max-w-5xl items-center justify-between gap-2 px-4">
				<a href={resolve('/')} class="flex items-center gap-2 text-lg font-bold tracking-tight">
					<KeyboardIcon class="size-5" aria-hidden="true" />
					{APP_TITLE}
				</a>
				<nav aria-label="เมนูหลัก" class="flex items-center gap-1 text-sm font-medium">
					{#each NAV as item (item.href)}
						{@const active = item.match(page.url.pathname)}
						<a
							href={item.href}
							aria-current={active ? 'page' : undefined}
							class={[
								'rounded-md px-3 py-1.5 transition-colors',
								active
									? 'bg-muted text-foreground'
									: 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
							]}
						>
							{item.label}
						</a>
					{/each}
				</nav>
			</div>
			{#if USE_MOCK}
				<p
					class="flex items-center justify-center gap-2 bg-fuchsia-100 px-4 py-1 text-center text-xs text-fuchsia-950"
					role="note"
					data-testid="mock-banner"
				>
					<FlaskConicalIcon class="size-3.5 shrink-0" aria-hidden="true" />
					โหมดจำลอง: ผลตรวจทั้งหมดเป็นข้อมูลจำลอง ไม่ได้มาจากโมเดลจริง
				</p>
			{/if}
		</header>

		<main class="mx-auto w-full max-w-5xl flex-1 px-4 py-5 sm:py-8">
			{@render children?.()}
		</main>

		<footer class="border-t px-4 py-3 text-center text-xs text-muted-foreground">
			KeyCheck ตรวจตำแหน่งคีย์แคป A–Z จากภาพถ่าย — ผลเป็นแนวทางประกอบ ควรตรวจซ้ำด้วยตาเมื่อไม่แน่ใจ
		</footer>
	</div>
	{#if dev}
		<SvelteQueryDevtools />
	{/if}
</QueryClientProvider>
