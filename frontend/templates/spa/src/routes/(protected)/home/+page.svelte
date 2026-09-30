<script lang="ts">
	import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { useHealthStatus } from '$lib/features/health/queries';
	import ArrowRightIcon from '@lucide/svelte/icons/arrow-right';
	import SparklesIcon from '@lucide/svelte/icons/sparkles';
	import CheckCircle2Icon from '@lucide/svelte/icons/check-circle-2';
	import LayersIcon from '@lucide/svelte/icons/layers';

	const healthQuery = useHealthStatus();
</script>

<div class="container mx-auto max-w-5xl p-6 space-y-8">
	<div>
		<h1 class="text-3xl font-bold tracking-tight">Dashboard</h1>
		<p class="text-muted-foreground mt-1">
			Welcome to your SvelteKitten SPA project. Explore the architecture or jump into building your domain features.
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

	<!-- Service Health Monitor -->
	<div class="space-y-3">
		<h2 class="text-lg font-semibold">Service Health Monitor</h2>
		<Card>
			<CardHeader>
				<div class="flex items-center justify-between">
					<CardTitle class="text-base">FastAPI Service Status</CardTitle>
					{#if healthQuery.isLoading}
						<div class="h-2.5 w-2.5 animate-pulse rounded-full bg-muted"></div>
					{:else if healthQuery.isError}
						<div class="h-2.5 w-2.5 rounded-full bg-destructive"></div>
					{:else if healthQuery.data}
						<div class="h-2.5 w-2.5 rounded-full bg-green-500"></div>
					{/if}
				</div>
				<CardDescription class="text-xs">
					Client-side reactive health polling against the backend service.
				</CardDescription>
			</CardHeader>
		</Card>
	</div>
</div>
