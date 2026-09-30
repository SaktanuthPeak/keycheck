function updatePackageJson(content, isSpa) {
    const pkg = JSON.parse(content);
    if (pkg.devDependencies?.['prettier-plugin-svelte']) {
        pkg.devDependencies['prettier-plugin-svelte'] = '^4.1.1';
    }
    if (isSpa) {
        pkg.engines = { ...pkg.engines, node: '>=20' };
    }
    return JSON.stringify(pkg, null, '\t') + '\n';
}
const codemod = {
    from: '0.3.6',
    to: '0.3.7',
    transforms: [
        {
            file: 'package.json',
            template: 'ssr',
            transform: (content) => updatePackageJson(content, false),
        },
        {
            file: 'package.json',
            template: 'spa',
            transform: (content) => updatePackageJson(content, true),
        },
    ],
};
export default codemod;
