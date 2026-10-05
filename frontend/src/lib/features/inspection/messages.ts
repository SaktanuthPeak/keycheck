// Thai UI copy for server enums. Never call scores "accuracy" (Spec §10.5).
import type { QuadError } from './geometry';
import type { InspectionStatus, Slot, SlotStatus, Stage } from './schema';

export const STAGES: readonly Stage[] = ['rectifying', 'detecting', 'reading', 'matching'];

export const STAGE_TEXT: Record<Stage, string> = {
	rectifying: 'ปรับมุมมองภาพให้ตรง',
	detecting: 'หาตำแหน่งปุ่ม',
	reading: 'อ่านตัวอักษรบนปุ่ม',
	matching: 'เทียบกับตำแหน่งที่ถูกต้อง'
};

export const STATUS_TEXT: Record<InspectionStatus, string> = {
	queued: 'รอคิวประมวลผล',
	processing: 'กำลังประมวลผล',
	completed: 'ประมวลผลเสร็จ',
	rejected: 'ตรวจไม่ได้',
	failed: 'ประมวลผลไม่สำเร็จ'
};

export const SLOT_STATUS_TEXT: Record<SlotStatus, string> = {
	correct: 'ถูก',
	incorrect: 'ผิด',
	uncertain: 'ไม่แน่ใจ'
};

/** Non-colour status glyphs (Spec §10.5: never rely on colour alone). */
export const SLOT_STATUS_GLYPH: Record<SlotStatus, string> = {
	correct: '✓',
	incorrect: '!',
	uncertain: '?'
};

const REASON_TEXT: Record<string, string> = {
	label_match: 'อ่านได้ตรงกับตัวที่ควรอยู่ในช่องนี้',
	label_mismatch: 'อ่านได้เป็นตัวอื่น ปุ่มนี้น่าจะอยู่ผิดช่อง',
	detection_unavailable: 'หาปุ่มในช่องนี้ไม่พบ',
	mapping_ambiguous: 'จับคู่ปุ่มกับช่องได้ไม่ชัดเจน',
	ocr_low_confidence: 'อ่านตัวอักษรได้ไม่ชัดพอจะยืนยัน',
	ocr_invalid_label: 'อ่านได้ไม่ใช่ตัวอักษร A–Z ตัวเดียว',
	crop_quality_low: 'ภาพบริเวณปุ่มนี้ไม่ชัด (เบลอ เงา หรือแสงสะท้อน)'
};

export function reasonText(reason: string): string {
	return REASON_TEXT[reason] ?? 'ระบบยืนยันผลช่องนี้ไม่ได้';
}

/** Below this the letter read on an uncertain slot is too weak to show even as a hint. */
export const CANDIDATE_MIN_SCORE = 0.8;

/**
 * Letter to suggest on an uncertain slot ("น่าจะเป็น X"), or null. The slot stays uncertain (yellow) and is never
 * counted as correct: the read was below the model's confirmation threshold.
 */
export function candidateHint(
	s: Pick<Slot, 'status' | 'candidate_label' | 'ocr_score'>
): string | null {
	if (s.status !== 'uncertain' || !s.candidate_label) return null;
	return (s.ocr_score ?? 0) >= CANDIDATE_MIN_SCORE ? s.candidate_label : null;
}

/** Score as a whole percent for hints, e.g. 0.948 -> "95%". */
export function percent(score: number | null): string {
	return score == null ? '' : `${Math.round(score * 100)}%`;
}

export type WarningInfo = { title: string; detail: string };

const WARNING_TEXT: Record<string, WarningInfo> = {
	layout_fit_not_checked: {
		title: 'ระบบตรวจไม่ได้ว่าแตะจุดอ้างอิงถูกช่อง',
		detail:
			'โมเดลรุ่นนี้ยังเทียบตำแหน่งปุ่มกับบล็อกตัวอักษรไม่ได้ ถ้าผลผิดทั้งแถวหรือเลื่อนไปหนึ่งช่อง ให้แตะจุด Q, P, M, Z ใหม่'
	},
	proxy_model: {
		title: 'โมเดลทดลอง',
		detail:
			'โมเดลนี้ฝึกจากข้อมูลตัวแทน (ภาพคีย์บอร์ด QWERTZ จาก Kaggle) ยังไม่ได้ประเมินกับภาพถ่ายคีย์บอร์ดจริง ใช้ผลเป็นแนวทางเท่านั้น'
	},
	image_quality_low: {
		title: 'ภาพไม่ค่อยชัด',
		detail: 'ภาพเบลอหรือแสงจ้า/มืดเกินไป ผลอาจคลาดเคลื่อน แนะนำให้ถ่ายใหม่ในที่แสงสม่ำเสมอ'
	}
};

export function warningInfo(code: string): WarningInfo {
	return WARNING_TEXT[code] ?? { title: 'ข้อควรระวัง', detail: code };
}

export function formatDateTime(iso: string | null | undefined): string {
	if (!iso) return '-';
	const d = new Date(iso);
	if (Number.isNaN(d.getTime())) return iso;
	return d.toLocaleString('th-TH', { dateStyle: 'medium', timeStyle: 'short' });
}

export const QUAD_ERROR_TEXT: Record<QuadError, string> = {
	bad_shape: 'ต้องมีจุดครบ 4 จุด',
	outside_image: 'มีจุดอยู่นอกภาพ',
	not_convex:
		'จุดไขว้กันหรือไม่เป็นรูปสี่เหลี่ยม — ตรวจลำดับ Q (ซ้ายบน) → P (ขวาบน) → M (ขวาล่าง) → Z (ซ้ายล่าง)',
	area_too_small: 'จุดอยู่ชิดกันเกินไป — ถ่ายให้บล็อกตัวอักษรใหญ่ขึ้นในภาพ หรือแตะจุดใหม่'
};
