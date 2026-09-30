export interface FileTransform {
    /** Relative path from project root, e.g. "src/lib/auth.ts" */
    file: string;
    /** If true, create the file even when it doesn't exist yet (transform receives empty string). */
    create?: boolean;
    /** Restrict this transform to a specific template type. Skipped when template doesn't match. */
    template?: 'ssr' | 'spa';
    transform: (content: string) => string;
}
export interface Codemod {
    from: string;
    to: string;
    transforms: FileTransform[];
}
/** Add new version modules here in ascending order. */
export declare const codemods: Codemod[];
/** Returns codemods that need to run to go from `currentVersion` to `targetVersion`. */
export declare function getApplicableCodemods(currentVersion: string, targetVersion: string): Codemod[];
