import { QueryClient } from '@tanstack/svelte-query';
import { isRetryable } from '$lib/features/inspection/errors';

export const prerender = true;
export const ssr = false;
export const trailingSlash = 'never';

export async function load() {
	const queryClient = new QueryClient({
		defaultOptions: {
			queries: {
				staleTime: 60 * 1000,
				retry: (failureCount, error) => isRetryable(error) && failureCount < 2
			},
			mutations: { retry: false }
		}
	});
	return { queryClient };
}
