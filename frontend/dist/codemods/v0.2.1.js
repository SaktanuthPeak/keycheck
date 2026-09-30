// SSR home page rewritten to demonstrate both fetch patterns side by side.
// +page.server.ts is new (no codemod needed — existing projects won't have it).
const homePage = `<script lang="ts">
\timport { createQuery } from '@tanstack/svelte-query';
\timport { Card, CardHeader, CardTitle, CardDescription } from '$lib/components/ui/card';
\timport * as api from '$lib/features/health/api';
\timport { healthKeys, useHealthStatus } from '$lib/features/health/queries';

\tlet { data } = $props();

\t// Pattern 1: SSR prefetch → TQ takes over client-side.
\t// Server load pre-fetches; initialData seeds the cache immediately (no loading flash).
\t// Use when SEO matters or first-paint data is critical.
\tconst ssrHealthQuery = createQuery(() => ({
\t\tqueryKey: [...healthKeys.all, 'ssr'],
\t\tqueryFn: () => api.healthStatus(),
\t\tinitialData: data.health ?? undefined,
\t\tstaleTime: 1000 * 60,
\t\trefetchInterval: 1000 * 60
\t}));

\t// Pattern 2: Client-only TQ.
\t// Server does no work; fetch happens entirely on the client after hydration.
\t// Use for user-specific data or when reducing server load matters.
\tconst clientHealthQuery = useHealthStatus();
<\/script>

<div class="container mx-auto p-6">
\t<h1 class="mb-6 text-3xl font-bold">Home</h1>
\t<div class="grid gap-4 sm:grid-cols-2">
\t\t<Card>
\t\t\t<CardHeader>
\t\t\t\t<div class="flex items-center gap-2">
\t\t\t\t\t<CardTitle>SSR + TQ</CardTitle>
\t\t\t\t\t{#if ssrHealthQuery.isLoading}
\t\t\t\t\t\t<div class="h-3 w-3 animate-pulse rounded-full bg-gray-300"></div>
\t\t\t\t\t{:else if ssrHealthQuery.isError}
\t\t\t\t\t\t<div class="h-3 w-3 rounded-full bg-red-500"></div>
\t\t\t\t\t{:else if ssrHealthQuery.data}
\t\t\t\t\t\t<div class="h-3 w-3 rounded-full bg-green-500"></div>
\t\t\t\t\t{/if}
\t\t\t\t</div>
\t\t\t\t<CardDescription>Server prefetch → TQ hydration. No loading flash, SEO-friendly.</CardDescription>
\t\t\t</CardHeader>
\t\t</Card>

\t\t<Card>
\t\t\t<CardHeader>
\t\t\t\t<div class="flex items-center gap-2">
\t\t\t\t\t<CardTitle>Client-only TQ</CardTitle>
\t\t\t\t\t{#if clientHealthQuery.isLoading}
\t\t\t\t\t\t<div class="h-3 w-3 animate-pulse rounded-full bg-gray-300"></div>
\t\t\t\t\t{:else if clientHealthQuery.isError}
\t\t\t\t\t\t<div class="h-3 w-3 rounded-full bg-red-500"></div>
\t\t\t\t\t{:else if clientHealthQuery.data}
\t\t\t\t\t\t<div class="h-3 w-3 rounded-full bg-green-500"></div>
\t\t\t\t\t{/if}
\t\t\t\t</div>
\t\t\t\t<CardDescription
\t\t\t\t\t>Fetches after hydration. Reduces server load, ideal for user-specific data.</CardDescription
\t\t\t\t>
\t\t\t</CardHeader>
\t\t</Card>
\t</div>
</div>
`;
const codemod = {
    from: '0.2.0',
    to: '0.2.1',
    transforms: [
        {
            // SSR only — SPA skips (file not found)
            file: 'src/routes/(protected)/home/+page.svelte',
            transform: () => homePage,
        },
    ],
};
export default codemod;
