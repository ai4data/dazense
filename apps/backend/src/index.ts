import './env';

import { startServer } from './app';
import dbConfig from './db/dbConfig';
import { runMigrations } from './db/migrate';

async function main() {
	await runMigrations({
		dbType: dbConfig.dialect,
		connectionString: dbConfig.dbUrl,
		migrationsPath: dbConfig.migrationsFolder,
	});

	await startServer({ port: 5005, host: '0.0.0.0' });
}

main().catch((err) => {
	console.error('\n❌ Server failed to start:\n');
	console.error(`   ${err.message}\n`);
	process.exit(1);
});
