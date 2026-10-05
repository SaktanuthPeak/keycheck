import {
	createInfiniteQuery,
	createMutation,
	createQuery,
	useQueryClient
} from '@tanstack/svelte-query';
import { POLL_INTERVAL_MS } from '$lib/config';
import { inspectionApi as defaultApi } from './default-api';
import { isRetryable, type ApiError } from './errors';
import type { InspectionApi } from './port';
import { isTerminal, type InspectionCreate, type Upload } from './schema';

export const inspectionKeys = {
	all: ['inspection'] as const,
	layouts: () => [...inspectionKeys.all, 'layouts'] as const,
	upload: (imageId: string) => [...inspectionKeys.all, 'upload', imageId] as const,
	detail: (id: string) => [...inspectionKeys.all, 'detail', id] as const,
	history: () => [...inspectionKeys.all, 'history'] as const
};

/** Retry only errors the contract marks retryable (network, 5xx, QUEUE_FULL ...). */
const retryRetryable = (max: number) => (failureCount: number, error: Error) =>
	isRetryable(error) && failureCount < max;

export function useLayouts(api: InspectionApi = defaultApi) {
	return createQuery<Awaited<ReturnType<InspectionApi['listLayouts']>>, ApiError>(() => ({
		queryKey: inspectionKeys.layouts(),
		queryFn: () => api.listLayouts(),
		staleTime: 10 * 60 * 1000,
		retry: retryRetryable(2)
	}));
}

/** Upload is not idempotent, so no automatic retry; the user retries explicitly. */
export function useUploadImage(api: InspectionApi = defaultApi) {
	const queryClient = useQueryClient();
	return createMutation<Upload, ApiError, File>(() => ({
		mutationFn: (file: File) => api.uploadImage(file),
		retry: false,
		onSuccess: (upload) => {
			queryClient.setQueryData(inspectionKeys.upload(upload.image_id), upload);
		}
	}));
}

/**
 * Create a job. Callers pass the same `client_request_id` for every retry of one submit attempt, so
 * automatic and manual retries are deduplicated by the backend and never create a second job.
 */
export function useCreateInspection(api: InspectionApi = defaultApi) {
	const queryClient = useQueryClient();
	return createMutation<
		Awaited<ReturnType<InspectionApi['createInspection']>>,
		ApiError,
		InspectionCreate
	>(() => ({
		mutationFn: (body: InspectionCreate) => api.createInspection(body),
		retry: retryRetryable(2),
		retryDelay: (n) => Math.min(1000 * 2 ** n, 4000),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: inspectionKeys.history() });
		}
	}));
}

/** Poll every POLL_INTERVAL_MS until a terminal status; stops when the page unmounts or is hidden. */
export function useInspection(getId: () => string, api: InspectionApi = defaultApi) {
	return createQuery<Awaited<ReturnType<InspectionApi['getInspection']>>, ApiError>(() => ({
		queryKey: inspectionKeys.detail(getId()),
		queryFn: () => api.getInspection(getId()),
		enabled: !!getId(),
		staleTime: 0,
		refetchInterval: (query) => (isTerminal(query.state.data?.status) ? false : POLL_INTERVAL_MS),
		refetchIntervalInBackground: false,
		retry: retryRetryable(3),
		retryDelay: (n) => Math.min(1000 * 2 ** n, 5000)
	}));
}

export function useInspectionHistory(api: InspectionApi = defaultApi) {
	return createInfiniteQuery(() => ({
		queryKey: inspectionKeys.history(),
		queryFn: ({ pageParam }: { pageParam: string | null }) =>
			api.listInspections({ limit: 20, cursor: pageParam }),
		initialPageParam: null as string | null,
		getNextPageParam: (last: Awaited<ReturnType<InspectionApi['listInspections']>>) =>
			last.next_cursor,
		staleTime: 0,
		retry: retryRetryable(2)
	}));
}

export function useDeleteInspection(api: InspectionApi = defaultApi) {
	const queryClient = useQueryClient();
	return createMutation<void, ApiError, string>(() => ({
		mutationFn: (id: string) => api.deleteInspection(id),
		onSuccess: (_data, id) => {
			queryClient.removeQueries({ queryKey: inspectionKeys.detail(id) });
			queryClient.invalidateQueries({ queryKey: inspectionKeys.history() });
		}
	}));
}
