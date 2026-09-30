import type { Handle } from '@sveltejs/kit';
import { sequence } from '@sveltejs/kit/hooks';
import { handleFastApiClient } from '$lib/hooks/fastapi.hook';
import { handleAuthGuard } from '$lib/hooks/auth-guard';

export const handle: Handle = sequence(handleAuthGuard, handleFastApiClient);
