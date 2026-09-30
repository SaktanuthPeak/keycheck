import { env } from '$env/dynamic/private';
import { logger } from '$lib/logger';
import { error } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { clearCookieTokens, setAuthTokens } from '$lib/utils/auth';

const handler: RequestHandler = async ({ request, cookies, params, fetch, url }) => {
	if (!env.BACKEND_API_URL) {
		logger.error('BACKEND_API_URL environment variable is not set.');
		throw new Error('BACKEND_API_URL environment variable is not set.');
	}

	const path = params.slug;
	const accessToken = cookies.get('access_token');
	const backendBase = env.BACKEND_API_URL.replace(/\/$/, '');
	const API_ENDPOINT = `${backendBase}/${path}${url.search}`;

	logger.debug(`${params.slug}`);
	logger.info(`[API Proxy] Forwarding request to: [${request.method}] ${API_ENDPOINT}`);

	// Clean up response headers that may cause client-side decoding errors
	const createProxyResponse = (originalResponse: Response): Response => {
		const headers = new Headers(originalResponse.headers);
		headers.delete('content-encoding');
		headers.delete('content-length');
		return new Response(originalResponse.body, {
			status: originalResponse.status,
			statusText: originalResponse.statusText,
			headers
		});
	};

	// Normalize request headers before forwarding
	const sanitizeRequestHeaders = (h: Headers) => {
		h.delete('host');
		h.delete('content-length');
		// remove other hop-by-hop headers if present
		h.delete('connection');
		h.delete('keep-alive');
		h.delete('proxy-authorization');
		h.delete('transfer-encoding');
		// Optionally prevent backend from sending compressed responses
		h.delete('accept-encoding');
		return h;
	};

	const makeApiRequest = (token?: string) => {
		const headers = sanitizeRequestHeaders(new Headers(request.headers));
		if (token) {
			logger.debug('[API Proxy] Using access token to forward request');
			headers.set('authorization', `Bearer ${token}`);
		} else {
			headers.delete('authorization');
		}

		const fetchOptions: RequestInit & { duplex?: 'half' } = {
			method: request.method,
			headers
		};

		if (request.method !== 'GET' && request.method !== 'HEAD' && request.body) {
			fetchOptions.duplex = 'half';
			fetchOptions.body = request.body;
		}

		return fetch(API_ENDPOINT, fetchOptions);
	};

	// Small helper to attempt refreshing the access token
	const tryRefresh = async (refreshToken?: string) => {
		if (!refreshToken) return undefined;
		const resp = await fetch(`${backendBase}/v1/auth/refresh`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				Authorization: `Bearer ${refreshToken}`
			}
		});

		if (!resp.ok) {
			logger.warn('[API Proxy] Refresh token invalid/expired, clearing cookies');
			clearCookieTokens(cookies);
			return undefined;
		}

		const data = await resp.json();
		setAuthTokens(cookies, data.access_token, data.refresh_token);
		return data.access_token as string | undefined;
	};

	try {
		let response = await makeApiRequest(accessToken);

		if (response.status === 401 && accessToken) {
			logger.warn(`[API Proxy] Unauthorized request, trying to refresh access token.`);
			const refreshToken = cookies.get('refresh_token');
			if (!refreshToken) {
				logger.warn(`[API Proxy] No Refresh Token`);
				clearCookieTokens(cookies);
				return createProxyResponse(response);
			}

			const newAccess = await tryRefresh(refreshToken);
			if (newAccess) {
				response = await makeApiRequest(newAccess);
			}
		}

		return createProxyResponse(response);
	} catch (err) {
		logger.error({ err }, `[API Proxy] Error fetching from API: [${request.method}] ${API_ENDPOINT}`);
		throw error(502, `Bad Gateway: Could not connect to API service. Please try again later.`);
	}
};

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
