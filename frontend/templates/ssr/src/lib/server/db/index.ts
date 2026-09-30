import Database from 'better-sqlite3';
import { drizzle } from 'drizzle-orm/better-sqlite3';
import * as schema from './schema';
import { env } from '$env/dynamic/private';
import { building } from '$app/environment';

const dbPath = env.DATABASE_URL || 'sqlite.db';
const sqlite = building ? new Database(':memory:') : new Database(dbPath);

if (!building) {
	sqlite.pragma('journal_mode = WAL');
	// Ensure tables exist on startup for zero-config out-of-the-box experience
	sqlite.exec(`
		CREATE TABLE IF NOT EXISTS users (
			id TEXT PRIMARY KEY,
			username TEXT NOT NULL UNIQUE,
			password_hash TEXT NOT NULL,
			created_at INTEGER NOT NULL
		);
		CREATE TABLE IF NOT EXISTS sessions (
			id TEXT PRIMARY KEY,
			user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
			expires_at INTEGER NOT NULL
		);
		CREATE TABLE IF NOT EXISTS items (
			id TEXT PRIMARY KEY,
			user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
			title TEXT NOT NULL,
			description TEXT,
			completed INTEGER NOT NULL DEFAULT 0,
			created_at INTEGER NOT NULL
		);
	`);
}

export const db = drizzle(sqlite, { schema });
