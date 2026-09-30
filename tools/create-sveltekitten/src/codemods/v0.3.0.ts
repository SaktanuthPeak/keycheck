import type { Codemod } from './index.js';

const codemod: Codemod = {
	from: '0.2.6',
	to: '0.3.0',
	transforms: [
		{
			file: '.env',
			template: 'ssr',
			transform: (content) => {
				if (content.includes('DATABASE_URL=')) return content;
				return `DATABASE_URL=sqlite.db\n${content}`;
			}
		},
		{
			file: 'package.json',
			template: 'ssr',
			transform: (content) => {
				try {
					const pkg = JSON.parse(content);
					pkg.scripts = pkg.scripts || {};
					if (!pkg.scripts['db:push']) pkg.scripts['db:push'] = 'drizzle-kit push';
					if (!pkg.scripts['db:generate']) pkg.scripts['db:generate'] = 'drizzle-kit generate';
					if (!pkg.scripts['db:migrate']) pkg.scripts['db:migrate'] = 'drizzle-kit migrate';
					if (!pkg.scripts['db:studio']) pkg.scripts['db:studio'] = 'drizzle-kit studio';

					pkg.dependencies = pkg.dependencies || {};
					if (!pkg.dependencies['better-sqlite3']) pkg.dependencies['better-sqlite3'] = '^11.8.1';
					if (!pkg.dependencies['drizzle-orm']) pkg.dependencies['drizzle-orm'] = '^0.39.3';

					pkg.devDependencies = pkg.devDependencies || {};
					if (!pkg.devDependencies['@types/better-sqlite3'])
						pkg.devDependencies['@types/better-sqlite3'] = '^7.6.12';
					if (!pkg.devDependencies['drizzle-kit']) pkg.devDependencies['drizzle-kit'] = '^0.30.4';

					return JSON.stringify(pkg, null, '\t') + '\n';
				} catch {
					return content;
				}
			}
		}
	]
};

export default codemod;
