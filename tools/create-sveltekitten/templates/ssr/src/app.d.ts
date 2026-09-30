// See https://svelte.dev/docs/kit/types#app.d.ts

import type { paths } from '$lib/api/paths/fastapi';
import type { Client } from 'openapi-fetch';
import type { User, Session } from '$lib/server/db/schema';

// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			user: User | null;
			session: Session | null;
			fastapiClient: Client<paths>;
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
		namespace Superforms {
			type Message = {
				type: 'error' | 'success';
				text: string;
				description?: string;
			};
		}
	}
}

export {};
