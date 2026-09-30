import { z } from 'zod';

export const itemSchema = z.object({
	id: z.string(),
	title: z.string().min(1, 'Title is required').max(100, 'Title must be 100 characters or less'),
	description: z.string().max(500, 'Description must be 500 characters or less').optional(),
	completed: z.boolean().default(false),
	createdAt: z.string()
});

export const createItemSchema = z.object({
	title: z.string().min(1, 'Title is required').max(100, 'Title must be 100 characters or less'),
	description: z.string().max(500, 'Description must be 500 characters or less').optional()
});

export type Item = z.infer<typeof itemSchema>;
export type CreateItemInput = z.infer<typeof createItemSchema>;
