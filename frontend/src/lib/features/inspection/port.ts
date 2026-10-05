import type {
	Inspection,
	InspectionAccepted,
	InspectionCreate,
	InspectionList,
	Layout,
	Upload
} from './schema';

/** API surface of the inspection feature (docs/api-contract.md §2). Errors are thrown as `ApiError`. */
export interface InspectionApi {
	/** True for the in-browser simulated implementation (UI must label results as simulated). */
	readonly simulated: boolean;
	listLayouts(): Promise<Layout[]>;
	uploadImage(file: File): Promise<Upload>;
	/** Absolute or same-origin URL of the backend-oriented image. */
	imageUrl(imageId: string): string;
	createInspection(body: InspectionCreate): Promise<InspectionAccepted>;
	getInspection(id: string): Promise<Inspection>;
	listInspections(params?: { limit?: number; cursor?: string | null }): Promise<InspectionList>;
	deleteInspection(id: string): Promise<void>;
}
