// Zod schemas for docs/api-contract.md §2.1 / §3. Unknown keys are stripped; contract fields are required.
import { z } from 'zod';

export const PointSchema = z.tuple([z.number(), z.number()]);
export type Point = z.infer<typeof PointSchema>;

export const QuadSchema = z.tuple([PointSchema, PointSchema, PointSchema, PointSchema]);
export type Quad = z.infer<typeof QuadSchema>;

export const ReferenceOrderSchema = z.enum(['TL', 'TR', 'BR', 'BL']);

export const LayoutSchema = z.object({
	layout_id: z.string(),
	version: z.number().int(),
	name: z.string(),
	supported_form_factors: z.array(z.string()),
	reference_points: z.array(
		z.object({ order: ReferenceOrderSchema, slot_id: z.string(), expected_label: z.string() })
	),
	slots: z.array(
		z.object({
			slot_id: z.string(),
			row: z.number().int(),
			col: z.number().int(),
			expected_label: z.string()
		})
	)
});
export type Layout = z.infer<typeof LayoutSchema>;

export const LayoutListSchema = z.object({ layouts: z.array(LayoutSchema) });

export const UploadSchema = z.object({
	image_id: z.string(),
	width: z.number().int().positive(),
	height: z.number().int().positive(),
	mime_type: z.string(),
	byte_size: z.number().int().nonnegative(),
	image_url: z.string(),
	created_at: z.string(),
	expires_at: z.string()
});
export type Upload = z.infer<typeof UploadSchema>;

export const InspectionCreateSchema = z.object({
	image_id: z.string().min(1),
	layout_id: z.string().min(1),
	reference_points_normalized: QuadSchema,
	client_request_id: z.string().optional()
});
export type InspectionCreate = z.infer<typeof InspectionCreateSchema>;

export const InspectionStatusSchema = z.enum([
	'queued',
	'processing',
	'completed',
	'rejected',
	'failed'
]);
export type InspectionStatus = z.infer<typeof InspectionStatusSchema>;

export const StageSchema = z.enum(['rectifying', 'detecting', 'reading', 'matching']);
export type Stage = z.infer<typeof StageSchema>;

export const InspectionAcceptedSchema = z.object({
	inspection_id: z.string(),
	status: InspectionStatusSchema,
	status_url: z.string()
});
export type InspectionAccepted = z.infer<typeof InspectionAcceptedSchema>;

export const SlotStatusSchema = z.enum(['correct', 'incorrect', 'uncertain']);
export type SlotStatus = z.infer<typeof SlotStatusSchema>;

export const SlotReasonSchema = z.enum([
	'label_match',
	'label_mismatch',
	'detection_unavailable',
	'mapping_ambiguous',
	'ocr_low_confidence',
	'ocr_invalid_label',
	'crop_quality_low'
]);
export type SlotReason = z.infer<typeof SlotReasonSchema>;

export const SlotSchema = z.object({
	slot_id: z.string(),
	row: z.number().int(),
	col: z.number().int(),
	expected_label: z.string(),
	observed_label: z.string().nullable(),
	// Letter read below the confidence threshold (uncertain + ocr_low_confidence): a hint, never a verdict.
	candidate_label: z.string().nullable().default(null),
	status: SlotStatusSchema,
	// Kept as string so a new backend reason code degrades to a generic message instead of a parse error.
	reason: z.string(),
	reason_codes: z.array(z.string()).default([]),
	detector_score: z.number().nullable(),
	ocr_score: z.number().nullable(),
	assignment_distance: z.number().nullable(),
	polygon: z.array(PointSchema).min(3),
	polygon_source: z.enum(['detection', 'layout']),
	is_reference: z.boolean().default(false)
});
export type Slot = z.infer<typeof SlotSchema>;

export const SummarySchema = z.object({
	total_slots: z.number().int(),
	correct: z.number().int(),
	incorrect: z.number().int(),
	uncertain: z.number().int()
});
export type Summary = z.infer<typeof SummarySchema>;

export const SuggestionSchema = z.object({
	type: z.enum(['swap_pair', 'cycle']),
	slots: z.array(z.string()).min(2)
});
export type Suggestion = z.infer<typeof SuggestionSchema>;

export const ErrorBodySchema = z.object({
	code: z.string(),
	message: z.string(),
	retryable: z.boolean()
});
export type ErrorBody = z.infer<typeof ErrorBodySchema>;

export const ApiErrorEnvelopeSchema = z.object({ error: ErrorBodySchema });

export const InspectionSchema = z.object({
	inspection_id: z.string(),
	status: InspectionStatusSchema,
	stage: StageSchema.nullable(),
	image_id: z.string(),
	image_url: z.string(),
	image_width: z.number().int().positive(),
	image_height: z.number().int().positive(),
	image_expired: z.boolean(),
	layout_id: z.string(),
	layout_version: z.number().int(),
	model_bundle_id: z.string().nullable(),
	coordinate_system: z.string(),
	reference_points_normalized: QuadSchema,
	created_at: z.string(),
	finished_at: z.string().nullable(),
	summary: SummarySchema.nullable(),
	slots: z.array(SlotSchema).default([]),
	suggestions: z.array(SuggestionSchema).default([]),
	warnings: z.array(z.string()).default([]),
	timings_ms: z.record(z.string(), z.number()).nullable(),
	error: ErrorBodySchema.nullable()
});
export type Inspection = z.infer<typeof InspectionSchema>;

// InspectionListItem is not spelled out in the contract (Should-have); accept a lenient subset.
export const InspectionListItemSchema = z.object({
	inspection_id: z.string(),
	status: InspectionStatusSchema,
	stage: StageSchema.nullable().optional(),
	created_at: z.string(),
	finished_at: z.string().nullable().optional(),
	image_expired: z.boolean().optional(),
	layout_id: z.string().optional(),
	summary: SummarySchema.nullable().optional(),
	error: ErrorBodySchema.nullable().optional()
});
export type InspectionListItem = z.infer<typeof InspectionListItemSchema>;

export const InspectionListSchema = z.object({
	items: z.array(InspectionListItemSchema),
	next_cursor: z.string().nullable()
});
export type InspectionList = z.infer<typeof InspectionListSchema>;

export const TERMINAL_STATUSES: readonly InspectionStatus[] = ['completed', 'rejected', 'failed'];

export function isTerminal(status: InspectionStatus | undefined | null): boolean {
	return !!status && TERMINAL_STATUSES.includes(status);
}
