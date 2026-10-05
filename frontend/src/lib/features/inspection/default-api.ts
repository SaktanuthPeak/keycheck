import { USE_MOCK } from '$lib/config';
import { httpInspectionApi } from './api';
import { mockInspectionApi } from './mock';
import type { InspectionApi } from './port';

/** Selected at build time by PUBLIC_USE_MOCK. */
export const inspectionApi: InspectionApi = USE_MOCK ? mockInspectionApi : httpInspectionApi;
