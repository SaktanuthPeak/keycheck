#!/usr/bin/env node
import * as p from '@clack/prompts';
import { cp, mkdir, readFile, writeFile, readdir, rename, unlink } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { styleText } from 'node:util';
import { patch } from './patch.js';
const __dirname = dirname(fileURLToPath(import.meta.url));
const TEMPLATES_DIR = join(__dirname, '../templates');
// @clack/prompts 1.x no longer dims note() body text by default; this restores the 0.x look.
const dimNote = { format: (line) => styleText('dim', line) };
async function getVersion() {
    const pkg = JSON.parse(await readFile(join(__dirname, '../package.json'), 'utf-8'));
    return pkg.version;
}
async function replaceInFile(filePath, replacements) {
    let content = await readFile(filePath, 'utf-8');
    for (const [from, to] of Object.entries(replacements)) {
        content = content.replaceAll(from, to);
    }
    await writeFile(filePath, content);
}
async function walkDir(dir) {
    const entries = await readdir(dir, { withFileTypes: true });
    const files = [];
    for (const entry of entries) {
        const fullPath = join(dir, entry.name);
        if (entry.isDirectory()) {
            files.push(...(await walkDir(fullPath)));
        }
        else {
            files.push(fullPath);
        }
    }
    return files;
}
/** npm omits `.gitignore` from packages; templates ship `_gitignore` instead. */
async function materializeGitignore(targetDir) {
    const underscore = join(targetDir, '_gitignore');
    const dot = join(targetDir, '.gitignore');
    if (!existsSync(underscore))
        return;
    if (existsSync(dot)) {
        await unlink(underscore);
    }
    else {
        await rename(underscore, dot);
    }
}
async function applyReplacements(targetDir, replacements) {
    const textExts = new Set([
        '.ts', '.svelte', '.js', '.json', '.css', '.html', '.md', '.env',
        '.prettierrc', '.gitignore', '.eslintrc', '.d.ts'
    ]);
    const files = await walkDir(targetDir);
    for (const file of files) {
        const ext = '.' + file.split('.').slice(1).join('.') || file;
        const basename = file.split('/').pop() ?? '';
        const isText = textExts.has('.' + (file.split('.').pop() ?? '')) ||
            basename.startsWith('.') ||
            !file.includes('.');
        if (isText) {
            try {
                await replaceInFile(file, replacements);
            }
            catch {
                // skip binary files
            }
        }
    }
}
async function main() {
    const version = await getVersion();
    p.intro(`create-sveltekitten v${version}`);
    const projectName = await p.text({
        message: 'Project name',
        placeholder: 'my-app',
        validate: (v) => (v?.trim() ? undefined : 'Required')
    });
    if (p.isCancel(projectName)) {
        p.cancel('Cancelled.');
        process.exit(0);
    }
    const template = await p.select({
        message: 'Template',
        options: [
            {
                value: 'ssr',
                label: 'SSR',
                hint: `v${version} · adapter-node · Drizzle SQLite / FastAPI BFF · server auth`
            },
            {
                value: 'spa',
                label: 'SPA',
                hint: `v${version} · adapter-static · client-side auth · TanStack Query`
            }
        ]
    });
    if (p.isCancel(template)) {
        p.cancel('Cancelled.');
        process.exit(0);
    }
    let ssrMode;
    let backendUrl = 'http://localhost:9000';
    if (template === 'ssr') {
        const mode = await p.select({
            message: 'Backend architecture for SSR',
            options: [
                {
                    value: 'fullstack',
                    label: 'SvelteKit Full-Stack (Integrated)',
                    hint: 'SQLite · Drizzle ORM · Server Actions · Local Database'
                },
                {
                    value: 'fastapi',
                    label: 'FastAPI Backend (BFF Proxy)',
                    hint: 'OpenAPI client · /api/proxy/** · External Python API'
                }
            ]
        });
        if (p.isCancel(mode)) {
            p.cancel('Cancelled.');
            process.exit(0);
        }
        ssrMode = mode;
        if (ssrMode === 'fastapi') {
            const url = await p.text({
                message: 'BACKEND_API_URL (FastAPI base URL)',
                placeholder: 'http://localhost:9000',
                initialValue: 'http://localhost:9000'
            });
            if (p.isCancel(url)) {
                p.cancel('Cancelled.');
                process.exit(0);
            }
            backendUrl = url;
        }
    }
    else {
        const url = await p.text({
            message: 'PUBLIC_API_URL (backend base URL)',
            placeholder: 'http://localhost:9000',
            initialValue: 'http://localhost:9000'
        });
        if (p.isCancel(url)) {
            p.cancel('Cancelled.');
            process.exit(0);
        }
        backendUrl = url;
    }
    const targetDir = join(process.cwd(), projectName);
    if (existsSync(targetDir)) {
        const overwrite = await p.confirm({
            message: `Directory "${projectName}" already exists. Overwrite?`,
            initialValue: false
        });
        if (!overwrite || p.isCancel(overwrite)) {
            p.cancel('Cancelled.');
            process.exit(0);
        }
    }
    const spinner = p.spinner();
    spinner.start('Scaffolding project...');
    try {
        await mkdir(targetDir, { recursive: true });
        const templateDir = join(TEMPLATES_DIR, template);
        await cp(templateDir, targetDir, { recursive: true, force: true });
        await materializeGitignore(targetDir);
        const replacements = {
            '{{PROJECT_NAME}}': projectName,
            '{{BACKEND_URL}}': backendUrl
        };
        await applyReplacements(targetDir, replacements);
        const envLines = template === 'ssr'
            ? `PUBLIC_APP_TITLE=${projectName}\nDATABASE_URL=sqlite.db\nBACKEND_API_URL=${backendUrl}\n`
            : `PUBLIC_APP_TITLE=${projectName}\nPUBLIC_API_URL=${backendUrl}\n`;
        await writeFile(join(targetDir, '.env'), envLines);
        await writeFile(join(targetDir, '.sveltekitten.json'), JSON.stringify({
            version: await getVersion(),
            template,
            ...(ssrMode ? { ssrMode } : {})
        }, null, '\t') + '\n');
        spinner.stop('Project scaffolded!');
    }
    catch (err) {
        spinner.stop('Failed.');
        p.log.error(String(err));
        process.exit(1);
    }
    if (template === 'ssr' && ssrMode === 'fullstack') {
        p.note([
            `cd ${projectName}`,
            'pnpm install',
            'pnpm dev'
        ].join('\n'), 'Next steps', dimNote);
        p.note([
            'Manage database schema & data:',
            '  pnpm db:push    # push schema changes to sqlite.db',
            '  pnpm db:studio  # open Drizzle Studio in browser',
            '  pnpm db:generate # generate SQL migrations'
        ].join('\n'), 'Database', dimNote);
    }
    else {
        p.note([`cd ${projectName}`, `pnpm install`, `pnpm dev`].join('\n'), 'Next steps', dimNote);
    }
    if (template === 'ssr' && ssrMode === 'fastapi') {
        p.note([
            'Fetch latest spec and regenerate types:',
            '  pnpm openapi:update',
            '',
            'Or regenerate from committed spec only:',
            '  pnpm openapi:fastapi'
        ].join('\n'), 'API types', dimNote);
    }
    p.outro('Happy coding!');
}
const command = process.argv[2];
if (command === 'patch') {
    getVersion()
        .then((v) => patch(v))
        .catch((err) => {
        console.error(err);
        process.exit(1);
    });
}
else {
    main().catch((err) => {
        console.error(err);
        process.exit(1);
    });
}
