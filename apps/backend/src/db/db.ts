import 'dotenv/config';

import { drizzle as drizzleSqlite } from 'drizzle-orm/libsql';
import { drizzle as drizzlePostgres } from 'drizzle-orm/node-postgres';
import { Pool } from 'pg';

import { isPostgres } from '../utils';
import * as postgresSchema from './pg-schema';
import * as sqliteSchema from './sqlite-schema';

export const db = isPostgres
	? drizzlePostgres(new Pool({ connectionString: process.env.DB_URL! }), { schema: postgresSchema })
	: drizzleSqlite(process.env.DB_FILE_NAME!, { schema: sqliteSchema });
/*import { Database } from 'bun:sqlite';
import { drizzle } from 'drizzle-orm/bun-sqlite';

const sqlite = new Database(process.env.DB_FILE_NAME ?? 'db.sqlite');
export const db = drizzle(sqlite);*/
