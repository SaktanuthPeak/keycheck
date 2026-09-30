import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';

export const users = sqliteTable('users', {
	id: text('id').primaryKey(),
	username: text('username').notNull().unique(),
	passwordHash: text('password_hash').notNull(),
	createdAt: integer('created_at', { mode: 'timestamp' }).notNull()
});

export const sessions = sqliteTable('sessions', {
	id: text('id').primaryKey(),
	userId: text('user_id')
		.notNull()
		.references(() => users.id, { onDelete: 'cascade' }),
	expiresAt: integer('expires_at', { mode: 'timestamp' }).notNull()
});

export const items = sqliteTable('items', {
	id: text('id').primaryKey(),
	userId: text('user_id').references(() => users.id, { onDelete: 'cascade' }),
	title: text('title').notNull(),
	description: text('description'),
	completed: integer('completed', { mode: 'boolean' }).notNull().default(false),
	createdAt: integer('created_at', { mode: 'timestamp' }).notNull()
});

export type User = {
	id: string;
	username: string;
	createdAt: Date;
};
export type Session = typeof sessions.$inferSelect;
export type DbItem = typeof items.$inferSelect;
