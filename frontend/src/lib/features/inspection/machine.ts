// Explicit UI state machine (Spec §10.6). Pure: no Svelte / $lib imports.
import type { InspectionStatus } from './schema';

export const FLOW_STATES = [
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
] as const;
export type FlowState = (typeof FLOW_STATES)[number];

export type FlowEvent =
	| 'OPEN_CAMERA' // idle -> camera_permission (asking permission / live viewfinder)
	| 'CLOSE_CAMERA' // camera_permission -> idle (cancel, denied, unsupported)
	| 'IMAGE_SELECTED' // photo captured or file chosen -> preview
	| 'RETAKE' // preview / calibrating -> idle (drop the local image)
	| 'UPLOAD' // preview -> uploading
	| 'UPLOAD_FAILED' // uploading -> preview (keep the image, allow retry)
	| 'UPLOADED' // uploading -> calibrating
	| 'SUBMITTED' // calibrating -> queued (202 accepted)
	| 'STARTED' // queued -> processing
	| 'COMPLETED'
	| 'REJECTED'
	| 'FAILED'
	| 'RECALIBRATE'; // rejected / failed -> calibrating (same image, new points)

const T: Record<FlowState, Partial<Record<FlowEvent, FlowState>>> = {
	idle: { OPEN_CAMERA: 'camera_permission', IMAGE_SELECTED: 'preview' },
	camera_permission: { CLOSE_CAMERA: 'idle', IMAGE_SELECTED: 'preview' },
	preview: { RETAKE: 'idle', UPLOAD: 'uploading', IMAGE_SELECTED: 'preview' },
	uploading: { UPLOAD_FAILED: 'preview', UPLOADED: 'calibrating' },
	calibrating: { SUBMITTED: 'queued', RETAKE: 'idle' },
	queued: { STARTED: 'processing', COMPLETED: 'completed', REJECTED: 'rejected', FAILED: 'failed' },
	processing: { COMPLETED: 'completed', REJECTED: 'rejected', FAILED: 'failed' },
	completed: { RETAKE: 'idle' },
	rejected: { RETAKE: 'idle', RECALIBRATE: 'calibrating' },
	failed: { RETAKE: 'idle', RECALIBRATE: 'calibrating' }
};

/** Next state, or the same state when the event is not allowed (ignored, never throws). */
export function transition(state: FlowState, event: FlowEvent): FlowState {
	return T[state][event] ?? state;
}

export function canTransition(state: FlowState, event: FlowEvent): boolean {
	return T[state][event] !== undefined;
}

/** Server job status maps 1:1 onto the last five UI states. */
export function stateFromStatus(status: InspectionStatus): FlowState {
	return status;
}
