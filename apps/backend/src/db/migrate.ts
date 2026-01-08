import { Database } from 'bun:sqlite';
import { drizzle } from 'drizzle-orm/bun-sqlite';
import { migrate } from 'drizzle-orm/bun-sqlite/migrator';
import path from 'path';

export async function runMigrations(dbPath: string, migrationsPath: string): Promise<void> {
	console.log(`🗃️  Opening database: ${dbPath}`);
	console.log(`📁 Migrations folder: ${migrationsPath}`);

	const sqlite = new Database(dbPath);
	const db = drizzle(sqlite);

	console.log('🚀 Running migrations...');

	try {
		migrate(db, { migrationsFolder: migrationsPath });
		console.log('✅ Migrations completed successfully!');
	} catch (error) {
		console.error('❌ Migration failed:', error);
		throw error;
	} finally {
		sqlite.close();
	}
}


