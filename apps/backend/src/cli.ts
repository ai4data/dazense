#!/usr/bin/env bun
/**
 * nao-chat-server CLI
 *
 * Usage:
 *   nao-chat-server migrate [--db <path>] [--migrations <path>]
 *   nao-chat-server serve [--port <port>] [--host <host>] [--db <path>]
 *   nao-chat-server (defaults to serve)
 */

import path from 'path';

import { runMigrations } from './db/migrate';

function getExecutableDir(): string {
	// When running as a compiled binary, Bun.main is the path to the binary
	return path.dirname(Bun.main);
}

function printHelp(): void {
	console.log(`
nao-chat-server - nao Chat Server

USAGE:
    nao-chat-server <command> [options]

COMMANDS:
    serve       Start the chat server (default)
    migrate     Run database migrations

OPTIONS:
    -h, --help  Show this help message

SERVE OPTIONS:
    --port <port>   Port to listen on (default: 5005)
    --host <host>   Host to bind to (default: 0.0.0.0)
    --db <path>     Database file path (default: ./db.sqlite)

MIGRATE OPTIONS:
    --db <path>          Database file path (default: ./db.sqlite)
    --migrations <path>  Migrations folder (default: ./migrations)

EXAMPLES:
    nao-chat-server serve --port 3000
    nao-chat-server migrate --db ./data/chat.db
    nao-chat-server migrate && nao-chat-server serve
`);
}

function parseArgs(args: string[]): { command: string; options: Record<string, string> } {
	const options: Record<string, string> = {};
	let command = 'serve'; // default command

	let i = 0;
	while (i < args.length) {
		const arg = args[i];

		if (arg === '-h' || arg === '--help') {
			options['help'] = 'true';
			i++;
		} else if (arg.startsWith('--')) {
			const key = arg.slice(2);
			const value = args[i + 1];
			if (value && !value.startsWith('-')) {
				options[key] = value;
				i += 2;
			} else {
				options[key] = 'true';
				i++;
			}
		} else if (!arg.startsWith('-')) {
			// First non-flag argument is the command
			if (command === 'serve' && (arg === 'migrate' || arg === 'serve')) {
				command = arg;
			}
			i++;
		} else {
			i++;
		}
	}

	return { command, options };
}

async function runServe(options: Record<string, string>): Promise<void> {
	const port = parseInt(options['port'] || '5005', 10);
	const host = options['host'] || '0.0.0.0';
	const dbPath = options['db'] || './db.sqlite';

	// Set environment variable for the database
	process.env.DB_FILE_NAME = dbPath;

	console.log(`🚀 Starting nao chat server...`);
	console.log(`   Database: ${dbPath}`);
	console.log(`   Listening on: ${host}:${port}`);

	// Dynamic import to ensure env vars are set first
	const { default: app } = await import('./app');

	try {
		const address = await app.listen({ host, port });
		console.log(`✅ Server is running on ${address}`);
	} catch (err) {
		app.log.error(err);
		process.exit(1);
	}
}

async function runMigrateCommand(options: Record<string, string>): Promise<void> {
	const execDir = getExecutableDir();
	const dbPath = options['db'] || './db.sqlite';
	const migrationsPath = options['migrations'] || path.join(execDir, 'migrations');

	try {
		await runMigrations(dbPath, migrationsPath);
	} catch {
		process.exit(1);
	}
}

async function main(): Promise<void> {
	const args = process.argv.slice(2);
	const { command, options } = parseArgs(args);

	if (options['help']) {
		printHelp();
		process.exit(0);
	}

	switch (command) {
		case 'migrate':
			await runMigrateCommand(options);
			break;
		case 'serve':
			await runServe(options);
			break;
		default:
			console.error(`Unknown command: ${command}`);
			printHelp();
			process.exit(1);
	}
}

main();


