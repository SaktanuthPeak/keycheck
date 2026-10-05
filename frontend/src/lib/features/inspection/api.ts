// HTTP implementation of InspectionApi (plain fetch; session cookie set by the backend).
import type { z } from 'zod';
import { API_BASE, API_ORIGIN } from '$lib/config';
import { ApiError, fromResponse, networkError } from './errors';
import type { InspectionApi } from './port';
import {
	InspectionAcceptedSchema,
	InspectionCreateSchema,
	InspectionListSchema,
	InspectionSchema,
	LayoutListSchema,
	UploadSchema,
	type InspectionCreate
} from './schema';

// Same-origin by default; an explicit cross-origin API needs 'include' to carry the session cookie.
const credentials: RequestCredentials = API_ORIGIN ? 'include' : 'same-origin';

async function send(path: string, init: RequestInit = {}): Promise<Response> {
	let res: Response;
	try {
		res = await fetch(`${API_BASE}${path}`, { credentials, ...init });
	} catch {
		throw networkError();
	}
	if (!res.ok) throw await fromResponse(res);
	return res;
}

async function json<S extends z.ZodType>(
	schema: S,
	path: string,
	init?: RequestInit
): Promise<z.infer<S>> {
	const res = await send(path, {
		...init,
		headers: { Accept: 'application/json', ...init?.headers }
	});
	let body: unknown;
	try {
		body = await res.json();
	} catch {
		throw new ApiError('INVALID_RESPONSE', '', true, res.status);
	}
	const parsed = schema.safeParse(body);
	if (!parsed.success)
		throw new ApiError('INVALID_RESPONSE', parsed.error.message, true, res.status);
	return parsed.data;
}

/** Resolve a contract URL such as `/api/v1/uploads/.../image` against the API origin. */
export function resolveApiUrl(url: string): string {
	return /^(https?:|blob:|data:)/.test(url) ? url : `${API_ORIGIN}${url}`;
}

export const httpInspectionApi: InspectionApi = {
	simulated: false,

	async listLayouts() {
		return (await json(LayoutListSchema, '/layouts')).layouts;
	},

	async uploadImage(file) {
		const form = new FormData();
		form.append('image', file, file.name || 'photo.jpg');
		const upload = await json(UploadSchema, '/uploads', { method: 'POST', body: form });
		return { ...upload, image_url: resolveApiUrl(upload.image_url) };
	},

	imageUrl(imageId) {
		return `${API_BASE}/uploads/${encodeURIComponent(imageId)}/image`;
	},

	async createInspection(body: InspectionCreate) {
		const payload = InspectionCreateSchema.parse(body);
		return json(InspectionAcceptedSchema, '/inspections', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});
	},

	async getInspection(id) {
		const ins = await json(InspectionSchema, `/inspections/${encodeURIComponent(id)}`);
		return { ...ins, image_url: resolveApiUrl(ins.image_url) };
	},

	async listInspections({ limit = 20, cursor } = {}) {
		const q = new URLSearchParams({ limit: String(limit) });
		if (cursor) q.set('cursor', cursor);
		return json(InspectionListSchema, `/inspections?${q}`);
	},

	async deleteInspection(id) {
		await send(`/inspections/${encodeURIComponent(id)}`, { method: 'DELETE' });
	}
};
