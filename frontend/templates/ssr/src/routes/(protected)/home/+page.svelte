<script lang="ts">
	import { createQuery } from '@tanstack/svelte-query';
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import * as api from '$lib/features/health/api';
	import { healthKeys, useHealthStatus } from '$lib/features/health/queries';
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import CheckCircle2Icon from '@lucide/svelte/icons/check-circle-2';
	import LayersIcon from '@lucide/svelte/icons/layers';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();

	// Pattern 1: SSR prefetch → TQ takes over client-side.
	const ssrHealthQuery = createQuery(() => ({
		queryKey: [...healthKeys.all, 'ssr'],
		queryFn: () => api.healthStatus(),
		initialData: data.health ?? undefined,
		staleTime: 1000 * 60,
		refetchInterval: 1000 * 60
	}));

	// Pattern 2: Client-only TQ.
	const clientHealthQuery = useHealthStatus();
</script>

<div class="container mx-auto max-w-5xl p-6 space-y-8">
	<div>
		<h1 class="text-3xl font-bold tracking-tight">Dashboard</h1>
		<p class="text-muted-foreground mt-1">
			Welcome to your SvelteKitten project. Explore the architecture or jump into building your domain features.
		</p>
	</div>

	<!-- Quickstart Cards -->
	<div class="grid gap-6 md:grid-cols-2">
		<!-- Example Feature Card -->
		<Card class="flex flex-col justify-between border-primary/20 bg-primary/5">
			<CardHeader>
				<div class="flex items-center gap-2">
					<SparklesIcon class="h-5 w-5 text-primary" />
					<CardTitle>Example CRUD Feature</CardTitle>
				</div>
				<CardDescription>
					Explore the isolated Items tracker demonstrating Svelte 5 runes, Zod validation, and TanStack Query mutations.
				</CardDescription>
			</CardHeader>
			<CardContent class="space-y-4">
				<div class="rounded-md bg-background/80 p-3 text-xs text-muted-foreground space-y-1">
					<p class="font-medium text-foreground">💡 How to replace or delete:</p>
					<p>1. Remove <code>src/lib/features/items/</code></p>
					<p>2. Remove <code>src/routes/(protected)/items/</code></p>
				</div>
				<Button href="/items" class="w-full sm:w-auto">
					Open Items Tracker
					<ArrowRightIcon class="h-4 w-4 ml-1" />
				</Button>
			</CardContent>
		</Card>

		<!-- Feature Architecture Info -->
		<Card>
			<CardHeader>
				<div class="flex items-center gap-2">
					<LayersIcon class="h-5 w-5 text-muted-foreground" />
					<CardTitle>Project Architecture</CardTitle>
				</div>
				<CardDescription>
					Standardized feature-slice convention for junior developers and AI assistants.
				</CardDescription>
			</CardHeader>
			<CardContent>
				<ul class="space-y-2 text-xs text-muted-foreground">
					<li class="flex items-center gap-2">
						<CheckCircle2Icon class="h-4 w-4 text-green-500 shrink-0" />
						<span><strong>Schema first:</strong> Zod schema defines types & validators</span>
					</li>
					<li class="flex items-center gap-2">
						<CheckCircle2Icon class="h-4 w-4 text-green-500 shrink-0" />
						<span><strong>Queries & Mutations:</strong> TanStack Query key factory</span>
					</li>
					<li class="flex items-center gap-2">
						<CheckCircle2Icon class="h-4 w-4 text-green-500 shrink-0" />
						<span><strong>Colocated UI:</strong> Feature components live inside <code>features/&lt;name&gt;/</code></span>
					</li>
				</ul>
			</CardContent>
		</Card>
	</div>

	<!-- System Health Indicators -->
	<div class="space-y-3">
		<h2 class="text-lg font-semibold">Service Health Monitors</h2>
		<div class="grid gap-4 sm:grid-cols-2">
			<Card>
				<CardHeader>
					<div class="flex items-center justify-between">
						<CardTitle class="text-base">SSR Prefetched Health</CardTitle>
						{#if ssrHealthQuery.isLoading}
							<div class="h-2.5 w-2.5 animate-pulse rounded-full bg-muted"></div>
						{:else if ssrHealthQuery.isError}
							<div class="h-2.5 w-2.5 rounded-full bg-destructive"></div>
						{:else if ssrHealthQuery.data}
							<div class="h-2.5 w-2.5 rounded-full bg-green-500"></div>
						{/if}
					</div>
					<CardDescription class="text-xs">
						Server prefetch → TanStack Query hydration. Zero layout shift, SEO friendly.
					</CardDescription>
				</CardHeader>
			</Card>

			<Card>
				<CardHeader>
					<div class="flex items-center justify-between">
						<CardTitle class="text-base">Client Reactive Health</CardTitle>
						{#if clientHealthQuery.isLoading}
							<div class="h-2.5 w-2.5 animate-pulse rounded-full bg-muted"></div>
						{:else if clientHealthQuery.isError}
							<div class="h-2.5 w-2.5 rounded-full bg-destructive"></div>
						{:else if clientHealthQuery.data}
							<div class="h-2.5 w-2.5 rounded-full bg-green-500"></div>
						{/if}
					</div>
					<CardDescription class="text-xs">
						Fetches on client hydration. Ideal for real-time and user-specific background polling.
					</CardDescription>
				</CardHeader>
			</Card>
		</div>
	</div>
</div>
