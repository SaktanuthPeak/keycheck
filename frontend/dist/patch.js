import * as p from '@clack/prompts';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { getApplicableCodemods } from './codemods/index.js';
export async function patch(latestVersion) {
    const configPath = join(process.cwd(), '.sveltekitten.json');
    if (!existsSync(configPath)) {
        p.log.error('No .sveltekitten.json found. This command must be run inside a project created by create-sveltekitten.');
        process.exit(1);
    }
    const config = JSON.parse(await readFile(configPath, 'utf-8'));
    const { version: currentVersion, template } = config;
    p.intro(`create-sveltekitten patch`);
    p.log.info(`Project: ${template} @ ${currentVersion} → ${latestVersion}`);
    if (currentVersion === latestVersion) {
        p.outro('Already up to date.');
        return;
    }
    const applicable = getApplicableCodemods(currentVersion, latestVersion);
    if (applicable.length === 0) {
        p.log.warn(`No codemods found for ${currentVersion} → ${latestVersion}. Update .sveltekitten.json manually if needed.`);
        p.outro('Done.');
        return;
    }
    const originalContent = new Map(); // undefined = file didn't exist yet
    const currentContent = new Map();
    const isNewFile = new Map();
    for (const codemod of applicable) {
        p.log.step(`Codemod ${codemod.from} → ${codemod.to}`);
        for (const t of codemod.transforms) {
            if (t.template && t.template !== template) {
                continue;
            }
            const filePath = join(process.cwd(), t.file);
            let oldContent;
            let firstEncounter = false;
            if (currentContent.has(t.file)) {
                oldContent = currentContent.get(t.file);
            }
            else if (existsSync(filePath)) {
                oldContent = await readFile(filePath, 'utf-8');
                originalContent.set(t.file, oldContent);
                firstEncounter = true;
            }
            else if (t.create) {
                oldContent = '';
                originalContent.set(t.file, undefined);
                isNewFile.set(t.file, true);
                firstEncounter = true;
            }
            else {
                p.log.warn(`  skip ${t.file} (not found)`);
                continue;
            }
            const newContent = t.transform(oldContent);
            currentContent.set(t.file, newContent);
            if (isNewFile.get(t.file) && firstEncounter) {
                p.log.info(`  create ${t.file}`);
            }
            else if (newContent === oldContent) {
                p.log.info(`  unchanged ${t.file}`);
            }
            else {
                p.log.info(`  modified ${t.file}`);
            }
        }
    }
    const pending = [];
    for (const [file, newContent] of currentContent) {
        if (newContent !== (originalContent.get(file) ?? '')) {
            pending.push({ file, newContent, isNew: isNewFile.get(file) ?? false });
        }
    }
    if (pending.length === 0) {
        p.log.info('No file changes needed.');
    }
    else {
        const confirm = await p.confirm({
            message: `Apply ${pending.length} file change(s) and update version to ${latestVersion}?`,
            initialValue: true
        });
        if (!confirm || p.isCancel(confirm)) {
            p.cancel('Patch cancelled.');
            return;
        }
        const spinner = p.spinner();
        spinner.start('Applying changes...');
        for (const { file, newContent, isNew } of pending) {
            const dest = join(process.cwd(), file);
            if (isNew)
                await mkdir(dirname(dest), { recursive: true });
            await writeFile(dest, newContent);
        }
        spinner.stop('Changes applied.');
    }
    // Always update version after running applicable codemods
    const updated = { ...config, version: latestVersion };
    await writeFile(configPath, JSON.stringify(updated, null, '\t') + '\n');
    p.outro(`Patched to ${latestVersion}. Commit .sveltekitten.json and changed files.`);
}
