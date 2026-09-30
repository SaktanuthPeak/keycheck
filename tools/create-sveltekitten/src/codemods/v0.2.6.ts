import type { Codemod } from './index.js';

const codemod: Codemod = {
	from: '0.2.5',
	to: '0.2.6',
	transforms: [
		{
			file: 'src/routes/(protected)/+layout.svelte',
			transform: (content) => {
				if (content.includes('href="/items"')) return content;
				// Add navigation link for items if not present
				if (content.includes('href="/home"')) {
					return content.replace(
						/<a\s+href="\/home"[^>]*>[\s\S]*?<\/a>/,
						(match) => `${match}\n\t\t\t\t<a href="/items" class="rounded-md px-3 py-1.5 transition-colors text-muted-foreground hover:text-foreground hover:bg-muted/50">Items</a>`
					);
				}
				return content;
			}
		}
	]
};

export default codemod;
