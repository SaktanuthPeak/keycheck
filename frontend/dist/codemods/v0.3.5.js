const DEP_UPDATES = {
    'better-sqlite3': '^13.0.3',
    'drizzle-orm': '^0.45.3',
};
const DEV_DEP_UPDATES = {
    '@types/better-sqlite3': '^9.6.0',
    'drizzle-kit': '^0.31.11',
};
function updatePackageJson(content) {
    const pkg = JSON.parse(content);
    if (pkg.dependencies) {
        for (const [name, ver] of Object.entries(DEP_UPDATES)) {
            if (pkg.dependencies[name]) {
                pkg.dependencies[name] = ver;
            }
        }
    }
    if (pkg.devDependencies) {
        for (const [name, ver] of Object.entries(DEV_DEP_UPDATES)) {
            if (pkg.devDependencies[name]) {
                pkg.devDependencies[name] = ver;
            }
        }
    }
    pkg.engines = { ...pkg.engines, node: '>=22' };
    return JSON.stringify(pkg, null, '\t') + '\n';
}
function updatePnpmWorkspace(content) {
    // better-sqlite3@13 ships prebuilt N-API binaries; allowing its install
    // script makes pnpm attempt a node-gyp rebuild that fails on machines
    // without a C/C++ toolchain, even though the prebuild works fine unbuilt.
    return content.replace(/(\n\s*better-sqlite3:\s*)true\b/, '$1false');
}
const codemod = {
    from: '0.3.4',
    to: '0.3.5',
    transforms: [
        {
            file: 'package.json',
            template: 'ssr',
            transform: updatePackageJson,
        },
        {
            file: 'pnpm-workspace.yaml',
            template: 'ssr',
            transform: updatePnpmWorkspace,
        },
    ],
};
export default codemod;
