// In-browser SIMULATED InspectionApi (PUBLIC_USE_MOCK=1). Results are fabricated for UI development only
// and are always labelled as simulated in the UI (Spec §17.3). State lives in memory: a reload loses it.
import { MAX_UPLOAD_BYTES } from '$lib/config';
import { ApiError, networkError } from './errors';
import {
	applyH,
	homography,
	KEY_HALF_U,
	LETTER_ROWS,
	REFERENCE_SLOTS,
	REFERENCE_U,
	slotCenterU,
	validateQuad,
	type Pt
} from './geometry';
import type { InspectionApi } from './port';
import type {
	Inspection,
	InspectionListItem,
	Layout,
	Quad,
	Slot,
	Stage,
	Suggestion,
	Upload
} from './schema';

/** sessionStorage key selecting a scenario: default | all_correct | layout_mismatch | failed | flaky_poll */
export const MOCK_SCENARIO_KEY = 'keycheck.mockScenario';
type Scenario = 'default' | 'all_correct' | 'layout_mismatch' | 'failed' | 'flaky_poll';

const LAYOUT: Layout = {
	layout_id: 'qwerty_stagger_letters_v1',
	version: 1,
	name: 'QWERTY row-staggered letter block (A-Z)',
	supported_form_factors: ['ANSI', 'ISO'],
	reference_points: REFERENCE_SLOTS.map(({ order, slot_id, expected_label }) => ({
		order,
		slot_id,
		expected_label
	})),
	slots: LETTER_ROWS.flatMap((letters, row) =>
		[...letters].map((expected_label, col) => ({
			slot_id: `r${row}c${col}`,
			row,
			col,
			expected_label
		}))
	)
};

// Timeline (ms after creation).
const QUEUED_MS = 1000;
const STAGE_MS = 800;
const DONE_MS = QUEUED_MS + 4 * STAGE_MS;
const STAGES: Stage[] = ['rectifying', 'detecting', 'reading', 'matching'];

type MockUpload = Upload & { blobUrl: string };
type MockJob = {
	id: string;
	imageId: string;
	points: Quad;
	createdAt: number;
	scenario: Scenario;
};

const uploads = new Map<string, MockUpload>();
const jobs = new Map<string, MockJob>();
const byClientRequestId = new Map<string, string>();

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const rid = (prefix: string) => `${prefix}_mock${Math.random().toString(36).slice(2, 10)}`;
const iso = (t: number) => new Date(t).toISOString();

function scenario(): Scenario {
	try {
		const v = sessionStorage.getItem(MOCK_SCENARIO_KEY);
		if (v === 'all_correct' || v === 'layout_mismatch' || v === 'failed' || v === 'flaky_poll') {
			return v;
		}
	} catch {
		// storage unavailable
	}
	return 'default';
}

async function sniffType(file: File): Promise<'image/jpeg' | 'image/png' | null> {
	const b = new Uint8Array(await file.slice(0, 8).arrayBuffer());
	if (b[0] === 0xff && b[1] === 0xd8 && b[2] === 0xff) return 'image/jpeg';
	if (b[0] === 0x89 && b[1] === 0x50 && b[2] === 0x4e && b[3] === 0x47) return 'image/png';
	return null;
}

async function imageSize(file: File): Promise<{ width: number; height: number }> {
	const bmp = await createImageBitmap(file, { imageOrientation: 'from-image' });
	const size = { width: bmp.width, height: bmp.height };
	bmp.close();
	return size;
}

function jitter(i: number, k: number): number {
	// Deterministic small offset so simulated detections do not look like perfect layout boxes.
	const s = Math.sin(i * 12.9898 + k * 78.233) * 43758.5453;
	return (s - Math.floor(s) - 0.5) * 0.06;
}

function buildSlots(points: Quad, sc: Scenario): { slots: Slot[]; suggestions: Suggestion[] } {
	const H = homography(REFERENCE_U, points as unknown as Pt[]);
	const swaps: Record<string, string> = sc === 'default' ? { r1c0: 'S', r1c1: 'A' } : {};
	const uncertain: Record<string, Slot['reason']> =
		sc === 'default' ? { r1c4: 'ocr_low_confidence', r2c4: 'detection_unavailable' } : {};
	const refIds = new Set<string>(REFERENCE_SLOTS.map((r) => r.slot_id));

	const slots = LAYOUT.slots.map((s, i): Slot => {
		const [cx, cy] = slotCenterU(s.row, s.col);
		const source = uncertain[s.slot_id] === 'detection_unavailable' ? 'layout' : 'detection';
		const h = KEY_HALF_U;
		const j = source === 'detection' ? (k: number) => jitter(i, k) : () => 0;
		const corners: Pt[] = [
			[cx - h + j(1), cy - h + j(2)],
			[cx + h + j(3), cy - h + j(4)],
			[cx + h + j(5), cy + h + j(6)],
			[cx - h + j(7), cy + h + j(8)]
		];
		const polygon = corners.map((p) => {
			const [x, y] = applyH(H, p);
			return [Math.min(1, Math.max(0, x)), Math.min(1, Math.max(0, y))] as [number, number];
		});
		const base = {
			slot_id: s.slot_id,
			row: s.row,
			col: s.col,
			expected_label: s.expected_label,
			polygon,
			polygon_source: source,
			is_reference: refIds.has(s.slot_id),
			detector_score: source === 'detection' ? 0.9 + jitter(i, 9) : null,
			assignment_distance: source === 'detection' ? Math.abs(jitter(i, 10)) : null
		} as const;
		if (swaps[s.slot_id]) {
			return {
				...base,
				observed_label: swaps[s.slot_id],
				status: 'incorrect',
				reason: 'label_mismatch',
				reason_codes: ['label_mismatch'],
				ocr_score: 0.93
			};
		}
		const reason = uncertain[s.slot_id];
		if (reason) {
			return {
				...base,
				observed_label: null,
				status: 'uncertain',
				reason,
				reason_codes: [reason],
				ocr_score: reason === 'ocr_low_confidence' ? 0.31 : null
			};
		}
		return {
			...base,
			observed_label: s.expected_label,
			status: 'correct',
			reason: 'label_match',
			reason_codes: ['label_match'],
			ocr_score: 0.95 + jitter(i, 11) / 2
		};
	});
	const suggestions: Suggestion[] =
		sc === 'default' ? [{ type: 'swap_pair', slots: ['r1c0', 'r1c1'] }] : [];
	return { slots, suggestions };
}

function view(job: MockJob, now = Date.now()): Inspection {
	const up = uploads.get(job.imageId);
	const age = now - job.createdAt;
	const done = age >= DONE_MS;
	const base: Inspection = {
		inspection_id: job.id,
		status: 'queued',
		stage: null,
		image_id: job.imageId,
		image_url: up?.blobUrl ?? '',
		image_width: up?.width ?? 1,
		image_height: up?.height ?? 1,
		image_expired: !up,
		layout_id: LAYOUT.layout_id,
		layout_version: LAYOUT.version,
		model_bundle_id: 'mock_simulated',
		coordinate_system: 'original_oriented_normalized',
		reference_points_normalized: job.points,
		created_at: iso(job.createdAt),
		finished_at: null,
		summary: null,
		slots: [],
		suggestions: [],
		warnings: [],
		timings_ms: null,
		error: null
	};
	if (age < QUEUED_MS) return base;
	if (!done) {
		const stage = STAGES[Math.min(3, Math.floor((age - QUEUED_MS) / STAGE_MS))];
		return { ...base, status: 'processing', stage };
	}
	const finished = { ...base, finished_at: iso(job.createdAt + DONE_MS) };
	if (job.scenario === 'layout_mismatch') {
		return {
			...finished,
			status: 'rejected',
			error: { code: 'LAYOUT_MISMATCH', message: 'ตำแหน่งปุ่มไม่เข้ากับ Layout', retryable: false }
		};
	}
	if (job.scenario === 'failed') {
		return {
			...finished,
			status: 'failed',
			error: { code: 'PROCESSING_FAILED', message: 'ประมวลผลไม่สำเร็จ', retryable: true }
		};
	}
	const { slots, suggestions } = buildSlots(job.points, job.scenario);
	const count = (st: Slot['status']) => slots.filter((s) => s.status === st).length;
	return {
		...finished,
		status: 'completed',
		summary: {
			total_slots: slots.length,
			correct: count('correct'),
			incorrect: count('incorrect'),
			uncertain: count('uncertain')
		},
		slots,
		suggestions,
		warnings: job.scenario === 'all_correct' ? ['layout_fit_not_checked'] : ['proxy_model'],
		timings_ms: null
	};
}

export const mockInspectionApi: InspectionApi = {
	simulated: true,

	async listLayouts() {
		await sleep(150);
		return [LAYOUT];
	},

	async uploadImage(file) {
		await sleep(600);
		if (file.size > MAX_UPLOAD_BYTES) throw new ApiError('IMAGE_TOO_LARGE', '', false, 413);
		const mime = await sniffType(file);
		if (!mime) throw new ApiError('UNSUPPORTED_IMAGE', '', false, 415);
		let size: { width: number; height: number };
		try {
			size = await imageSize(file);
		} catch {
			throw new ApiError('IMAGE_DECODE_FAILED', '', false, 422);
		}
		const now = Date.now();
		const blobUrl = URL.createObjectURL(file);
		const upload: Upload = {
			image_id: rid('img'),
			...size,
			mime_type: mime,
			byte_size: file.size,
			image_url: blobUrl,
			created_at: iso(now),
			expires_at: iso(now + 24 * 3600_000)
		};
		uploads.set(upload.image_id, { ...upload, blobUrl });
		return upload;
	},

	imageUrl(imageId) {
		return uploads.get(imageId)?.blobUrl ?? '';
	},

	async createInspection(body) {
		await sleep(300);
		if (body.client_request_id) {
			const existing = byClientRequestId.get(body.client_request_id);
			if (existing) return { inspection_id: existing, status: 'queued', status_url: '' };
		}
		if (!uploads.has(body.image_id)) throw new ApiError('NOT_FOUND', '', false, 404);
		if (body.layout_id !== LAYOUT.layout_id) throw new ApiError('LAYOUT_NOT_FOUND', '', false, 422);
		if (validateQuad(body.reference_points_normalized)) {
			throw new ApiError('INVALID_CORNERS', '', true, 422);
		}
		const job: MockJob = {
			id: rid('ins'),
			imageId: body.image_id,
			points: body.reference_points_normalized,
			createdAt: Date.now(),
			scenario: scenario()
		};
		jobs.set(job.id, job);
		if (body.client_request_id) byClientRequestId.set(body.client_request_id, job.id);
		return {
			inspection_id: job.id,
			status: 'queued',
			status_url: `/api/v1/inspections/${job.id}`
		};
	},

	async getInspection(id) {
		await sleep(150);
		const job = jobs.get(id);
		if (!job) throw new ApiError('NOT_FOUND', '', false, 404);
		const age = Date.now() - job.createdAt;
		if (job.scenario === 'flaky_poll' && age > 1200 && age < 3200) throw networkError();
		return view(job);
	},

	async listInspections({ limit = 20 } = {}) {
		await sleep(150);
		const items: InspectionListItem[] = [...jobs.values()]
			.sort((a, b) => b.createdAt - a.createdAt)
			.slice(0, limit)
			.map((job) => {
				const v = view(job);
				return {
					inspection_id: v.inspection_id,
					status: v.status,
					stage: v.stage,
					created_at: v.created_at,
					finished_at: v.finished_at,
					image_expired: v.image_expired,
					layout_id: v.layout_id,
					summary: v.summary,
					error: v.error
				};
			});
		return { items, next_cursor: null };
	},

	async deleteInspection(id) {
		await sleep(150);
		const job = jobs.get(id);
		if (!job) throw new ApiError('NOT_FOUND', '', false, 404);
		if (Date.now() - job.createdAt < DONE_MS) {
			throw new ApiError('INSPECTION_IN_PROGRESS', '', false, 409);
		}
		jobs.delete(id);
	}
};
