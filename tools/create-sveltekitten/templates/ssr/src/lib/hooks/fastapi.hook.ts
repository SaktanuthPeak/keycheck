import { createFastApiClient } from '$lib/api/fastapi-client';
import type { Handle } from '@sveltejs/kit';

export const handleFastApiClient: Handle = async ({ event, resolve }) => {
	// Handle FastAPI requests here
	event.locals.fastapiClient = createFastApiClient(event);

	const response = await resolve(event);
	return response;
};
