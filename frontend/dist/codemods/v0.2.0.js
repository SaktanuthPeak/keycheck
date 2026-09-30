const codemod = {
    from: '0.1.1',
    to: '0.2.0',
    transforms: [
        {
            file: 'package.json',
            transform: (content) => {
                // SSR: split openapi:fastapi (live URL) into fetch + generate + update scripts
                content = content.replace(`"openapi:fastapi": "openapi-typescript http://localhost:9000/openapi.json -o src/lib/api/paths/fastapi.d.ts"`, `"openapi:fetch": "mkdir -p src/libs/api-specs && curl -f http://localhost:9000/openapi.json -o src/libs/api-specs/fastapi.json",\n\t\t"openapi:fastapi": "openapi-typescript src/libs/api-specs/fastapi.json -o src/lib/api/paths/fastapi.d.ts",\n\t\t"openapi:update": "pnpm openapi:fetch && pnpm openapi:fastapi"`);
                // SPA: replace single openapi script (live URL) with split workflow
                content = content.replace(`"openapi": "openapi-typescript http://localhost:9000/openapi.json -o ./src/lib/api/openapi.d.ts"`, `"openapi": "openapi-typescript",\n\t\t"openapi:fetch": "mkdir -p src/libs/api-specs && curl -f http://localhost:9000/openapi.json -o src/libs/api-specs/fastapi.json",\n\t\t"openapi:fastapi": "openapi-typescript src/libs/api-specs/fastapi.json -o src/lib/api/openapi.d.ts",\n\t\t"openapi:update": "pnpm openapi:fetch && pnpm openapi:fastapi"`);
                return content;
            },
        },
        {
            file: '.gitignore',
            transform: (content) => {
                const additions = [];
                if (!content.includes('src/lib/api/paths/'))
                    additions.push('src/lib/api/paths/');
                if (!content.includes('src/lib/api/openapi.d.ts'))
                    additions.push('src/lib/api/openapi.d.ts');
                if (additions.length === 0)
                    return content;
                return content.trimEnd() + '\n\n# openapi generated types\n' + additions.join('\n') + '\n';
            },
        },
    ],
};
export default codemod;
