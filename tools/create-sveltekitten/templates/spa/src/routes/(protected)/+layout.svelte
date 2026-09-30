<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import { authStore } from '$lib/stores/auth.svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import client from '$lib/api/client';
	import { toast } from 'svelte-sonner';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();

	async function logout() {
		authStore.logout();
		await client.POST('/v1/auth/logout', { credentials: 'include' });
		toast.success('Logged out successfully');
		await goto('/login');
	}
</script>

<div class="flex min-h-svh flex-col">
	<header class="flex items-center justify-between border-b px-6 py-3">
		<div class="flex items-center gap-6">
			<a href="/home" class="font-bold tracking-tight text-lg text-primary">SvelteKitten</a>
			<nav class="flex items-center gap-1 text-sm font-medium">
				<a
					href="/home"
					class="rounded-md px-3 py-1.5 transition-colors {page.url.pathname === '/home'
						? 'bg-muted text-foreground'
						: 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}"
				>
					Home
				</a>
				<a
					href="/items"
					class="rounded-md px-3 py-1.5 transition-colors {page.url.pathname.startsWith('/items')
						? 'bg-muted text-foreground'
						: 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}"
				>
					Items
				</a>
			</nav>
		</div>

		<div class="flex items-center gap-4">
			<span class="text-muted-foreground text-sm">{authStore.user?.username}</span>
			<Separator orientation="vertical" class="h-4" />
			<Button variant="outline" size="sm" onclick={logout}>Logout</Button>
		</div>
	</header>

	<main class="flex-1">
		{@render children()}
	</main>
</div>
