// Browser-free tests of pure modules (run by the Playwright "unit" project).
import { expect, test } from '@playwright/test';
import {
	applyH,
	homography,
	REFERENCE_U,
	slotCenterU,
	validateQuad,
	type Pt
} from '../src/lib/features/inspection/geometry';
import { canTransition, FLOW_STATES, transition } from '../src/lib/features/inspection/machine';

const GOOD: Pt[] = [
	[0.125, 0.286],
	[0.8, 0.286],
	[0.631, 0.543],
	[0.181, 0.543]
];

test.describe('validateQuad (same rule as ai/preprocessing/geometry.py)', () => {
	test('accepts a convex TL,TR,BR,BL quad in either winding', () => {
		expect(validateQuad(GOOD)).toBeNull();
		expect(validateQuad([...GOOD].reverse())).toBeNull();
	});

	test('rejects crossing order (Q,P,Z,M)', () => {
		expect(validateQuad([GOOD[0], GOOD[1], GOOD[3], GOOD[2]])).toBe('not_convex');
	});

	test('rejects concave quad', () => {
		expect(
			validateQuad([
				[0.1, 0.1],
				[0.9, 0.1],
				[0.5, 0.2],
				[0.1, 0.9]
			])
		).toBe('not_convex');
	});

	test('rejects points outside 0..1, wrong count, non-finite', () => {
		expect(validateQuad([[-0.01, 0.2], GOOD[1], GOOD[2], GOOD[3]])).toBe('outside_image');
		expect(validateQuad(GOOD.slice(0, 3))).toBe('bad_shape');
		expect(validateQuad([[Number.NaN, 0.2], GOOD[1], GOOD[2], GOOD[3]])).toBe('bad_shape');
	});

	test('rejects area below 0.002 of the image', () => {
		const tiny: Pt[] = [
			[0.5, 0.5],
			[0.54, 0.5],
			[0.54, 0.54],
			[0.5, 0.54]
		]; // area 0.0016
		expect(validateQuad(tiny)).toBe('area_too_small');
	});
});

test('homography maps reference slots onto tapped points and stagger centres in between', () => {
	const H = homography(REFERENCE_U, GOOD);
	REFERENCE_U.forEach((u, i) => {
		const [x, y] = applyH(H, u);
		expect(x).toBeCloseTo(GOOD[i][0], 6);
		expect(y).toBeCloseTo(GOOD[i][1], 6);
	});
	expect(slotCenterU(1, 0)).toEqual([0.25, 1]);
	expect(slotCenterU(2, 6)).toEqual([6.75, 2]);
});

test.describe('UI state machine (Spec §10.6)', () => {
	test('has exactly the ten spec states', () => {
		expect([...FLOW_STATES]).toEqual([
			'idle',
			'camera_permission',
			'preview',
			'uploading',
			'calibrating',
			'queued',
			'processing',
			'completed',
			'rejected',
			'failed'
		]);
	});

	test('happy path', () => {
		let s = transition('idle', 'OPEN_CAMERA');
		expect(s).toBe('camera_permission');
		s = transition(s, 'IMAGE_SELECTED');
		expect(s).toBe('preview');
		s = transition(s, 'UPLOAD');
		expect(s).toBe('uploading');
		s = transition(s, 'UPLOADED');
		expect(s).toBe('calibrating');
		s = transition(s, 'SUBMITTED');
		expect(s).toBe('queued');
		s = transition(s, 'STARTED');
		expect(s).toBe('processing');
		expect(transition(s, 'COMPLETED')).toBe('completed');
	});

	test('upload failure returns to preview; illegal events are ignored', () => {
		expect(transition('uploading', 'UPLOAD_FAILED')).toBe('preview');
		expect(transition('idle', 'SUBMITTED')).toBe('idle');
		expect(canTransition('completed', 'SUBMITTED')).toBe(false);
		expect(transition('rejected', 'RECALIBRATE')).toBe('calibrating');
	});
});
