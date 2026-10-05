// Client-side pre-checks before upload; the backend re-validates by magic bytes (contract §3).
import { MAX_UPLOAD_BYTES } from '$lib/config';
import { errorMessage } from './errors';

const HEIC = /\.(heic|heif)$/i;
const ALLOWED = ['image/jpeg', 'image/png'];

/** Thai error message, or null when the file may be uploaded. */
export function checkLocalFile(file: File): string | null {
	const type = file.type.toLowerCase();
	if (type.startsWith('image/hei') || HEIC.test(file.name)) return errorMessage('HEIC_UNSUPPORTED');
	// Empty type (some Android pickers) is left to the backend sniffing.
	if (type && !ALLOWED.includes(type)) return errorMessage('UNSUPPORTED_IMAGE');
	if (file.size > MAX_UPLOAD_BYTES) return errorMessage('IMAGE_TOO_LARGE');
	if (file.size === 0) return errorMessage('IMAGE_DECODE_FAILED');
	return null;
}
