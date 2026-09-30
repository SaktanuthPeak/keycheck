const OLD_UPDATE_COMPLETION = `export async function updateItemCompletion(id: string, completed: boolean): Promise<void> {
	db.update(items).set({ completed }).where(eq(items.id, id)).run();
}`;
const NEW_UPDATE_COMPLETION = `export async function updateItemCompletion(
	id: string,
	completed: boolean
): Promise<DbItem | undefined> {
	return db.update(items).set({ completed }).where(eq(items.id, id)).returning().get();
}`;
const OLD_PATCH_HANDLER = `		await updateItemCompletion(id, completed);
		return json({ success: true });`;
const NEW_PATCH_HANDLER = `		const updated = await updateItemCompletion(id, completed);
		if (!updated) {
			return json({ error: 'Item not found' }, { status: 404 });
		}
		return json(updated);`;
const OLD_TOGGLE_ITEM = `	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.error || 'Failed to update item');
	}
	return {
		id,
		title: '',
		completed,
		createdAt: new Date().toISOString()
	};
}`;
const NEW_TOGGLE_ITEM = `	if (!res.ok) {
		const err = await res.json().catch(() => ({}));
		throw new Error(err.error || 'Failed to update item');
	}
	const data = await res.json();
	return {
		...data,
		description: data.description ?? undefined,
		createdAt: typeof data.createdAt === 'string' ? data.createdAt : new Date(data.createdAt).toISOString()
	};
}`;
const codemod = {
    from: '0.3.0',
    to: '0.3.1',
    transforms: [
        {
            // PATCH /api/items previously returned { success: true } instead of the updated
            // row, so the client had to fabricate a fake Item (empty title) in api.ts.
            file: 'src/lib/features/items/server.ts',
            template: 'ssr',
            transform: (content) => {
                if (!content.includes(OLD_UPDATE_COMPLETION))
                    return content;
                return content.replace(OLD_UPDATE_COMPLETION, NEW_UPDATE_COMPLETION);
            }
        },
        {
            file: 'src/routes/api/items/+server.ts',
            template: 'ssr',
            transform: (content) => {
                if (!content.includes(OLD_PATCH_HANDLER))
                    return content;
                return content.replace(OLD_PATCH_HANDLER, NEW_PATCH_HANDLER);
            }
        },
        {
            file: 'src/lib/features/items/api.ts',
            template: 'ssr',
            transform: (content) => {
                if (!content.includes(OLD_TOGGLE_ITEM))
                    return content;
                return content.replace(OLD_TOGGLE_ITEM, NEW_TOGGLE_ITEM);
            }
        }
    ]
};
export default codemod;
