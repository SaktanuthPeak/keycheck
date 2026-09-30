import v0_1_1 from './v0.1.1.js';
import v0_2_0 from './v0.2.0.js';
import v0_2_1 from './v0.2.1.js';
import v0_2_2 from './v0.2.2.js';
import v0_2_3 from './v0.2.3.js';
import v0_2_4 from './v0.2.4.js';
import v0_2_5 from './v0.2.5.js';
import v0_2_6 from './v0.2.6.js';
import v0_3_0 from './v0.3.0.js';
import v0_3_1 from './v0.3.1.js';
import v0_3_2 from './v0.3.2.js';
import v0_3_3 from './v0.3.3.js';
import v0_3_4 from './v0.3.4.js';
import v0_3_5 from './v0.3.5.js';
import v0_3_7 from './v0.3.7.js';
/** Add new version modules here in ascending order. */
export const codemods = [
    v0_1_1,
    v0_2_0,
    v0_2_1,
    v0_2_2,
    v0_2_3,
    v0_2_4,
    v0_2_5,
    v0_2_6,
    v0_3_0,
    v0_3_1,
    v0_3_2,
    v0_3_3,
    v0_3_4,
    v0_3_5,
    v0_3_7
];
function parseVersion(v) {
    const [major = 0, minor = 0, patch = 0] = v.split('.').map(Number);
    return [major, minor, patch];
}
function versionGt(a, b) {
    const [aMaj, aMin, aPat] = parseVersion(a);
    const [bMaj, bMin, bPat] = parseVersion(b);
    if (aMaj !== bMaj)
        return aMaj > bMaj;
    if (aMin !== bMin)
        return aMin > bMin;
    return aPat > bPat;
}
/** Returns codemods that need to run to go from `currentVersion` to `targetVersion`. */
export function getApplicableCodemods(currentVersion, targetVersion) {
    return codemods.filter((c) => versionGt(c.to, currentVersion) && !versionGt(c.to, targetVersion));
}
