<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Separator } from '$lib/components/ui/separator';
	import { page } from '$app/state';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();
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
			<span class="text-muted-foreground text-sm">{data.user.username}</span>
			<Separator orientation="vertical" class="h-4" />
			<form method="POST" action="/logout">
				<Button type="submit" variant="outline" size="sm">Logout</Button>
			</form>
		</div>
	</header>

	<main class="flex-1">
		{@render children()}
	</main>
</div>
