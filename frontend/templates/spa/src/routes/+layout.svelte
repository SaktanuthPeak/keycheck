<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { QueryClientProvider } from '@tanstack/svelte-query';
	import { Toaster } from '$lib/components/ui/sonner/index.js';
	import { PUBLIC_APP_TITLE } from '$env/static/public';
	import { SvelteQueryDevtools } from '@tanstack/svelte-query-devtools';

	let { children, data } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>
		{PUBLIC_APP_TITLE}
	</title>
</svelte:head>

<Toaster position="top-right" richColors />

<QueryClientProvider client={data.queryClient}>
	{@render children?.()}
	<SvelteQueryDevtools />
</QueryClientProvider>
