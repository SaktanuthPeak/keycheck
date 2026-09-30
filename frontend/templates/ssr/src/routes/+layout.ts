import { QueryClient } from '@tanstack/svelte-query';

export async function load() {
	const queryClient = new QueryClient({
		defaultOptions: {
			queries: {
				staleTime: 60 * 1000,
				retry: 1
			}
		}
	});
	return { queryClient };
}
