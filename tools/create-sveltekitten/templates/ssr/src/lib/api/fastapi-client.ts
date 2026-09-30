import createClient from 'openapi-fetch';
import type { paths } from './paths/fastapi';

// Define a clear type for the SvelteKit event object for server-side usage.
type ServerEvent = {
	fetch: typeof fetch;
	url: URL;
};

export function createFastApiClient(event?: ServerEvent) {
	const client = createClient<paths>({
		baseUrl: event ? `${event?.url.origin}/api/proxy` : '/api/proxy',
		fetch: event ? event.fetch : fetch
	});

	return client;
}

const fastapiClient = createFastApiClient();

export default fastapiClient;
