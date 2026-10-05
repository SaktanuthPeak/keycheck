// Pure geometry helpers (no $lib / $env imports so they can be unit tested directly).
export type Pt = readonly [number, number];

export type QuadError = 'bad_shape' | 'outside_image' | 'not_convex' | 'area_too_small';

/** Same rule as backend ai/preprocessing/geometry.py `validate_reference_points` (min_area_frac=0.002). */
export const MIN_AREA_FRAC = 0.002;

/**
 * Validate 4 normalised points (TL, TR, BR, BL). Equivalent to the backend check on pixel coordinates
 * because x*w, y*h is a positive scaling: inside-image, cross-product signs and area/(w*h) are preserved.
 */
export function validateQuad(pts: readonly Pt[]): QuadError | null {
	if (pts.length !== 4 || !pts.every((p) => p.length === 2 && p.every(Number.isFinite))) {
		return 'bad_shape';
	}
	if (pts.some(([x, y]) => x < 0 || y < 0 || x > 1 || y > 1)) return 'outside_image';
	const cross: number[] = [];
	for (let i = 0; i < 4; i++) {
		const a = pts[i];
		const b = pts[(i + 1) % 4];
		const c = pts[(i + 2) % 4];
		cross.push((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]));
	}
	if (!(cross.every((v) => v > 0) || cross.every((v) => v < 0))) return 'not_convex';
	if (polygonArea(pts) < MIN_AREA_FRAC) return 'area_too_small';
	return null;
}

export function polygonArea(pts: readonly Pt[]): number {
	let s = 0;
	for (let i = 0; i < pts.length; i++) {
		const [x0, y0] = pts[i];
		const [x1, y1] = pts[(i + 1) % pts.length];
		s += x0 * y1 - x1 * y0;
	}
	return Math.abs(s) / 2;
}

export function centroid(pts: readonly Pt[]): [number, number] {
	const n = pts.length || 1;
	return [pts.reduce((s, p) => s + p[0], 0) / n, pts.reduce((s, p) => s + p[1], 0) / n];
}

export const clamp01 = (v: number) => Math.min(1, Math.max(0, v));

/** 3x3 homography (row-major, 9 numbers) mapping 4 src points onto 4 dst points. */
export function homography(src: readonly Pt[], dst: readonly Pt[]): number[] {
	const A: number[][] = [];
	const b: number[] = [];
	for (let i = 0; i < 4; i++) {
		const [x, y] = src[i];
		const [u, v] = dst[i];
		A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]);
		b.push(u);
		A.push([0, 0, 0, x, y, 1, -v * x, -v * y]);
		b.push(v);
	}
	return [...solve(A, b), 1];
}

export function applyH(H: readonly number[], [x, y]: Pt): [number, number] {
	const w = H[6] * x + H[7] * y + H[8];
	return [(H[0] * x + H[1] * y + H[2]) / w, (H[3] * x + H[4] * y + H[5]) / w];
}

function solve(A: number[][], b: number[]): number[] {
	const n = b.length;
	const M = A.map((row, i) => [...row, b[i]]);
	for (let c = 0; c < n; c++) {
		let p = c;
		for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
		if (Math.abs(M[p][c]) < 1e-12) throw new Error('singular');
		[M[c], M[p]] = [M[p], M[c]];
		for (let r = 0; r < n; r++) {
			if (r === c) continue;
			const f = M[r][c] / M[c][c];
			for (let k = c; k <= n; k++) M[r][k] -= f * M[c][k];
		}
	}
	return M.map((row, i) => row[n] / row[i]);
}

// Generic row-staggered letter block in key units u (Spec §7.2, layouts/qwerty_stagger_letters_v1.json).
export const LETTER_ROWS = ['QWERTYUIOP', 'ASDFGHJKL', 'ZXCVBNM'] as const;
export const ROW_OFFSET_U = [0, 0.25, 0.75] as const;
export const KEY_HALF_U = 0.45;

export function slotCenterU(row: number, col: number): [number, number] {
	return [col + (ROW_OFFSET_U[row] ?? 0), row];
}

/** Reference slots in TL, TR, BR, BL order = centres of Q, P, M, Z by position. */
export const REFERENCE_SLOTS = [
	{ order: 'TL', slot_id: 'r0c0', row: 0, col: 0, expected_label: 'Q' },
	{ order: 'TR', slot_id: 'r0c9', row: 0, col: 9, expected_label: 'P' },
	{ order: 'BR', slot_id: 'r2c6', row: 2, col: 6, expected_label: 'M' },
	{ order: 'BL', slot_id: 'r2c0', row: 2, col: 0, expected_label: 'Z' }
] as const;

export const REFERENCE_U: Pt[] = REFERENCE_SLOTS.map((r) => slotCenterU(r.row, r.col));
