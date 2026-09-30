import { cp } from 'node:fs/promises';

for (const template of ['spa', 'ssr']) {
	await cp(`templates/${template}/.gitignore`, `templates/${template}/_gitignore`);
}
