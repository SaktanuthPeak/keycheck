// Error contract (docs/api-contract.md §3) -> typed error + Thai user messages.
import { ApiErrorEnvelopeSchema, type ErrorBody } from './schema';

/** Client-side codes in addition to the backend ones. */
export type ClientErrorCode = 'NETWORK_ERROR' | 'INVALID_RESPONSE' | 'HEIC_UNSUPPORTED';

export class ApiError extends Error {
	readonly code: string;
	readonly retryable: boolean;
	readonly status: number;
	/** Server message (Thai per contract); kept for fallback only. */
	readonly serverMessage: string;

	constructor(code: string, serverMessage: string, retryable: boolean, status = 0) {
		super(errorMessage(code, serverMessage));
		this.name = 'ApiError';
		this.code = code;
		this.retryable = retryable;
		this.status = status;
		this.serverMessage = serverMessage;
	}
}

const MESSAGES: Record<string, string> = {
	UNSUPPORTED_IMAGE:
		'ไฟล์นี้ไม่ใช่ภาพ JPEG หรือ PNG (รวมถึง HEIC) กรุณาแปลงเป็น JPEG/PNG แล้วลองใหม่',
	HEIC_UNSUPPORTED:
		'ยังไม่รองรับไฟล์ HEIC/HEIF กรุณาตั้งกล้องเป็น JPEG ("เข้ากันได้มากที่สุด") หรือแปลงเป็น JPEG/PNG ก่อน',
	IMAGE_TOO_LARGE: 'ภาพใหญ่เกินกำหนด (ไม่เกิน 15 MiB และ 24 ล้านพิกเซล) กรุณาลดขนาดแล้วลองใหม่',
	IMAGE_DECODE_FAILED: 'เปิดไฟล์ภาพนี้ไม่ได้ ไฟล์อาจเสีย กรุณาถ่ายหรือเลือกภาพใหม่',
	INVALID_CORNERS:
		'จุดอ้างอิงไม่ถูกต้อง (ต้องครบ 4 จุด ไม่ไขว้กัน และไม่เล็กเกินไป) กรุณาแตะจุดใหม่',
	LAYOUT_NOT_FOUND: 'ไม่พบรูปแบบคีย์บอร์ดที่เลือก กรุณาโหลดหน้าใหม่',
	VALIDATION_ERROR: 'ข้อมูลที่ส่งไม่ถูกต้อง กรุณาลองใหม่',
	NOT_FOUND: 'ไม่พบข้อมูลนี้ อาจถูกลบไปแล้วหรือเป็นของอุปกรณ์อื่น',
	IMAGE_EXPIRED: 'ภาพนี้ถูกลบตามระยะเวลาเก็บรักษาแล้ว กรุณาถ่ายภาพใหม่',
	IMAGE_IN_USE: 'ลบภาพไม่ได้ เพราะยังมีงานตรวจที่ใช้ภาพนี้อยู่',
	INSPECTION_IN_PROGRESS: 'ลบไม่ได้ระหว่างที่งานยังประมวลผลอยู่',
	QUEUE_FULL: 'ขณะนี้มีงานรอคิวมาก กรุณารอสักครู่แล้วลองใหม่',
	ORIGIN_FORBIDDEN: 'คำขอถูกปฏิเสธเพราะมาจากต้นทางที่ไม่ได้รับอนุญาต',
	MODEL_UNAVAILABLE: 'ระบบตรวจยังไม่พร้อมใช้งาน กรุณาลองใหม่ภายหลัง',
	LAYOUT_MISMATCH:
		'ตำแหน่งปุ่มในภาพไม่เข้ากับบล็อกตัวอักษร QWERTY แถวเยื้อง: อาจแตะจุดอ้างอิงผิดช่อง หรือคีย์บอร์ดรุ่นนี้อาจไม่รองรับ (เช่น Ortholinear/Split)',
	PROCESSING_FAILED: 'ประมวลผลไม่สำเร็จ กรุณาลองส่งตรวจอีกครั้ง',
	INTERNAL_ERROR: 'ระบบขัดข้อง กรุณาลองใหม่อีกครั้ง',
	NETWORK_ERROR: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาตรวจอินเทอร์เน็ตแล้วลองใหม่',
	INVALID_RESPONSE: 'ข้อมูลจากเซิร์ฟเวอร์ไม่ตรงรูปแบบที่คาดไว้ กรุณาลองใหม่'
};

export function errorMessage(code: string, fallback?: string): string {
	return MESSAGES[code] ?? (fallback || MESSAGES.INTERNAL_ERROR);
}

export function fromErrorBody(body: ErrorBody, status = 0): ApiError {
	return new ApiError(body.code, body.message, body.retryable, status);
}

/** Build an ApiError from a non-2xx response; tolerates non-contract bodies (e.g. proxy HTML). */
export async function fromResponse(res: Response): Promise<ApiError> {
	let body: unknown = null;
	try {
		body = await res.json();
	} catch {
		// not JSON
	}
	const parsed = ApiErrorEnvelopeSchema.safeParse(body);
	if (parsed.success) return fromErrorBody(parsed.data.error, res.status);
	const retryable = res.status >= 500 || res.status === 429 || res.status === 408;
	const code =
		res.status === 404 ? 'NOT_FOUND' : res.status === 410 ? 'IMAGE_EXPIRED' : 'INTERNAL_ERROR';
	return new ApiError(code, '', retryable, res.status);
}

export function networkError(): ApiError {
	return new ApiError('NETWORK_ERROR', '', true);
}

export function toApiError(err: unknown): ApiError {
	if (err instanceof ApiError) return err;
	return new ApiError('INTERNAL_ERROR', err instanceof Error ? err.message : '', true);
}

export function isRetryable(err: unknown): boolean {
	return err instanceof ApiError ? err.retryable : false;
}
