import { createQuery } from '@tanstack/svelte-query';
import * as api from './api';

export const healthKeys = {
	all: ['health'] as const,
	status: () => [...healthKeys.all, 'status'] as const
};

export const useHealthStatus = () => {
	return createQuery(() => ({
		queryKey: healthKeys.status(),
		queryFn: () => api.healthStatus(),
		staleTime: 1000 * 60,
		refetchInterval: 1000 * 60
	}));
};
