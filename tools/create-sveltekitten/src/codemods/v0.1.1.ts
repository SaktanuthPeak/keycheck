import type { Codemod } from './index.js';

const codemod: Codemod = {
	from: '0.1.0',
	to: '0.1.1',
	transforms: [
		{
			// SSR only — SPA skips (file not found)
			file: 'src/lib/features/login/components/form.svelte',
			transform: (content) =>
				content.replace(
					`import { LoaderCircle } from 'lucide-svelte';`,
					`import LoaderCircle from '@lucide/svelte/icons/loader-circle';`
				),
		},
	],
};

export default codemod;
