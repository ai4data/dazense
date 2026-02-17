# dazense Architecture

## Current Architecture

### Overview

dazense is a monorepo with three runtime components and a CLI:

```
                    Browser
                      |
                      v
              +---------------+
              |   Frontend    |  React, TanStack, Shadcn
              |  :3000 (dev)  |  Vite dev server
              +-------+-------+
                      |
                      | tRPC + HTTP
                      v
              +---------------+
              |   Backend     |  Fastify, tRPC, Drizzle, Vercel AI SDK
              |    :5005      |  Bun runtime
              +-------+-------+
                      |
          +-----------+-----------+
          |                       |
          v                       v
  +---------------+       +---------------+
  |   FastAPI     |       |   LLM API     |  Anthropic, OpenAI,
  |    :8005      |       |  (external)   |  Mistral, Google,
  |  Python tools |       +---------------+  OpenRouter
  +-------+-------+
          |
          v
  +---------------+
  |   Database    |  DuckDB, PostgreSQL, BigQuery,
  |  (user data)  |  Snowflake, Databricks, MSSQL
  +---------------+
```

### Component Details

#### CLI (`cli/`)

Python package (`dazense-core`) published to PyPI. Entry point: `dazense_core/main.py`.

| Command     | What it does                                                                                                                       |
| ----------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `dazense init`  | Scaffolds a project — prompts for databases, LLM provider, creates `dazense_config.yaml` and `RULES.md`                                |
| `dazense sync`  | Connects to databases, generates schema markdown files under `databases/`, syncs git repos, Notion pages, renders Jinja2 templates |
| `dazense chat`  | Launches the backend binary + FastAPI server, opens browser                                                                        |
| `dazense debug` | Tests database and LLM connectivity                                                                                                |
| `dazense test`  | Runs evaluation tests against YAML test cases                                                                                      |

**Key dependency:** Ibis Framework with adapters for DuckDB, PostgreSQL, BigQuery, Snowflake, Databricks, MSSQL.

**Sync output structure:**

```
project/
├── dazense_config.yaml
├── RULES.md
├── databases/
│   └── type={db_type}/
│       └── database={db_name}/
│           └── schema={schema}/
│               └── table={table}/
│                   ├── columns.md       # Column names, types, nullable
│                   ├── description.md   # Row count, metadata
│                   └── preview.md       # Sample rows
├── repos/                               # Cloned git repos
├── docs/                                # Synced Notion pages, other docs
├── agent/mcps/                          # MCP tool configs
├── templates/                           # User Jinja2 templates
└── tests/                               # Evaluation test cases
```

#### Backend (`apps/backend/`)

TypeScript, runs on Bun. Fastify HTTP server with tRPC for typed API.

**Layers:**

```
routes/          tRPC procedures + Fastify HTTP routes
  |
services/        Business logic (agent execution, Slack, email)
  |
queries/         Drizzle ORM database queries
  |
db/              Schema definitions (SQLite or PostgreSQL)
```

**Key files:**

| File                               | Purpose                                                    |
| ---------------------------------- | ---------------------------------------------------------- |
| `src/index.ts`                     | Entry point, starts server on :5005                        |
| `src/services/agent.service.ts`    | Core agent loop — builds messages, streams LLM responses   |
| `src/components/system-prompt.tsx` | Builds the system prompt with project context              |
| `src/agents/tools/index.ts`        | Registers all agent tools                                  |
| `src/agents/tools/execute-sql.ts`  | SQL execution tool — calls FastAPI                         |
| `src/agents/providers.ts`          | LLM provider configuration                                 |
| `src/agents/user-rules.ts`         | Loads RULES.md and database connections into system prompt |
| `src/trpc/router.ts`               | Root tRPC router                                           |
| `src/auth.ts`                      | Better-Auth setup                                          |

**Agent execution flow:**

```
1. User sends message via tRPC (chat.routes.ts)
2. AgentManager loads project context (agent.service.ts)
3. System prompt built: fixed instructions + RULES.md + database connections (system-prompt.tsx)
4. Messages sent to LLM via Vercel AI SDK (agent.service.ts)
5. LLM calls tools (execute_sql, read, grep, list, search, display_chart, etc.)
6. Tool results returned to LLM
7. LLM generates final response
8. Response streamed to frontend
```

**Tool context:** Every tool receives only `{ projectFolder: string }`. All context comes from files in that folder or from the system prompt.

#### FastAPI Server (`apps/backend/fastapi/`)

Python, runs on uvicorn at :8005. Handles operations that need Python runtime.

**Endpoints:**

| Endpoint               | Purpose                                      |
| ---------------------- | -------------------------------------------- |
| `POST /execute_sql`    | Executes SQL against user databases via Ibis |
| `POST /execute_python` | Runs Python code in sandbox                  |

**SQL execution flow:**

```
1. Agent tool calls HTTP POST to localhost:8005/execute_sql
2. FastAPI loads dazense_config.yaml from project folder
3. Resolves which database to use (single DB or by database_id)
4. Connects via Ibis (DuckDB, Postgres, BigQuery, etc.)
5. Executes SQL, returns results as JSON
```

#### Frontend (`apps/frontend/`)

React 19, Vite, TanStack Router (file-based routing), TanStack Query, Shadcn UI.

**Key structure:**

```
src/
├── routes/              File-based routing (TanStack Router)
├── components/
│   ├── ui/              Shadcn components
│   ├── tool-calls/      Tool execution result rendering
│   └── (feature components)
├── hooks/               React hooks
├── contexts/            Theme, sidebar, analytics providers
├── services/            API client logic
├── queries/             React Query definitions
└── lib/                 Utilities
```

**Communication:** tRPC client with HTTP batch link to backend.

#### Database (internal)

Stores application state (not user data). Supports SQLite (default) or PostgreSQL.

**Key tables:** user, session, chat, chat_message, message_feedback, project, organization, saved_prompts.

**ORM:** Drizzle with separate schemas for SQLite and PostgreSQL.

---

## New Architecture (with Semantic Layer + Business Rules)

### Overview

Two new components are added to the existing architecture. Both live in the FastAPI Python server, since they depend on Ibis (already there) and Python (already there).

```
                    Browser
                      |
                      v
              +---------------+
              |   Frontend    |
              |  :3000 (dev)  |
              +-------+-------+
                      |
                      v
              +---------------+
              |   Backend     |
              |    :5005      |
              +-------+-------+
                      |
          +-----------+-----------+------------------+
          |                       |                  |
          v                       v                  v
  +---------------+       +---------------+  +---------------+
  |   FastAPI     |       |   LLM API     |  |   App DB      |
  |    :8005      |       |  (external)   |  | SQLite / PG   |
  |               |       +---------------+  +---------------+
  | /execute_sql  |
  | /execute_py   |
  | /query_metrics|  <-- NEW
  | /business_ctx |  <-- NEW
  +-------+-------+
          |
    +-----+-----+
    |     |     |
    v     v     v
  +---+ +---+ +---+
  |Ibis| |Sem| |Biz|
  |    | |Lyr| |Rul|
  +---+ +---+ +---+
    |     |
    v     v
  +---------------+
  |   Database    |
  |  (user data)  |
  +---------------+
```

### What changes

#### 1. New module: Semantic Layer (`cli/dazense_core/semantic/`)

A YAML-to-Ibis translator. Pure Python, no external dependencies beyond Ibis.

**Files:**

```
cli/dazense_core/semantic/
├── __init__.py
├── model.py          # Parse semantic_model.yml into Python objects
├── compiler.py       # Translate metric queries into Ibis expressions
└── validator.py      # Validate model against actual database schema
```

**Responsibilities:**

- Parse `semantic_model.yml` from project folder
- Validate measure/dimension references against database schema
- Resolve joins between models
- Compile `query(measures, dimensions, filters)` into Ibis expression
- Let Ibis handle SQL dialect compilation

**Data flow:**

```
semantic_model.yml
        |
        v
  +-----------+
  | model.py  |  Parse YAML into SemanticModel objects
  +-----------+
        |
        v
  +-------------+
  | compiler.py |  Resolve joins, build Ibis aggregation
  +-------------+
        |
        v
  +-------------+
  |    Ibis     |  Compile to target SQL dialect
  +-------------+
        |
        v
  +-------------+
  |  Database   |  Execute query, return results
  +-------------+
```

**SemanticModel structure:**

```python
@dataclass
class Measure:
    name: str
    expression: str        # e.g., "_.amount.sum()"

@dataclass
class Dimension:
    name: str
    expression: str        # e.g., "_.status"

@dataclass
class Join:
    model: str             # target model name
    type: str              # "one" or "many"
    on: str                # e.g., "_.customer_id"

@dataclass
class Model:
    name: str
    table: str
    primary_key: str | None
    time_dimension: str | None
    measures: dict[str, Measure]
    dimensions: dict[str, Dimension]
    joins: dict[str, Join]

@dataclass
class SemanticModel:
    models: dict[str, Model]
```

#### 2. New module: Business Rules (`cli/dazense_core/rules/`)

A YAML-based business rules engine. Pure Python, no rdflib.

**Files:**

```
cli/dazense_core/rules/
├── __init__.py
├── loader.py         # Parse business_rules.yml
└── engine.py         # Match rules to concepts, return relevant context
```

**Responsibilities:**

- Parse `business_rules.yml` from project folder
- Match rules to data concepts (by metric name, dimension, keyword)
- Return relevant caveats, guidance, and classifications
- Inject critical rules into system prompt

#### 3. New FastAPI endpoints

Added to `apps/backend/fastapi/main.py`:

**`POST /query_metrics`**

```
Request:
{
  "dazense_project_folder": "/path/to/project",
  "measures": ["order_count", "total_amount"],
  "dimensions": ["status"],
  "filters": { "status": "completed" },
  "order_by": [["total_amount", "desc"]],
  "limit": 10
}

Response:
{
  "data": [
    { "status": "completed", "order_count": 450, "total_amount": 89234.50 },
    ...
  ],
  "columns": ["status", "order_count", "total_amount"],
  "row_count": 3,
  "sql": "SELECT status, COUNT(*), SUM(amount) FROM orders WHERE..."
}
```

**`POST /get_business_context`**

```
Request:
{
  "dazense_project_folder": "/path/to/project",
  "concepts": ["tips", "cash"],
  "context_type": "caveats"      # or "classifications" or "all"
}

Response:
{
  "rules": [
    {
      "name": "cash_tips_not_recorded",
      "severity": "critical",
      "description": "Cash tips are NOT recorded in the data",
      "guidance": "Exclude cash payments from any tip analysis"
    }
  ]
}
```

#### 4. New agent tools

Added to `apps/backend/src/agents/tools/`:

**`query-metrics.ts`** — Calls `/query_metrics` on FastAPI. Same HTTP pattern as `execute-sql.ts`.

```typescript
// Input schema for the LLM
{
  measures: string[]      // e.g., ["order_count", "total_amount"]
  dimensions?: string[]   // e.g., ["status", "customer.name"]
  filters?: object        // e.g., { status: "completed" }
  order_by?: [string, "asc" | "desc"][]
  limit?: number
}
```

**`get-business-context.ts`** — Calls `/get_business_context` on FastAPI.

```typescript
// Input schema for the LLM
{
  concepts: string[]      // e.g., ["tips", "cash_payments"]
}
```

#### 5. System prompt changes

In `apps/backend/src/components/system-prompt.tsx`:

- If `semantic_model.yml` exists in the project folder, inject a section listing available metrics and dimensions
- Add instructions: "Use query_metrics for defined metrics. Use execute_sql for ad-hoc exploration."
- If `business_rules.yml` exists, inject critical rules (severity: critical) directly into the system prompt
- Add instructions: "Call get_business_context when interpreting results or answering 'why' questions."

#### 6. CLI changes

In `cli/dazense_core/commands/sync/`:

- During `dazense sync`, validate `semantic_model.yml` against actual database schema if both exist
- Report warnings for undefined tables, missing columns, invalid expressions

In `cli/dazense_core/commands/init/`:

- Optionally scaffold a starter `semantic_model.yml` based on discovered tables
- Auto-generate basic measures (count, sum of numeric columns) and dimensions (string/date columns)

### What does NOT change

- Frontend — no changes needed. Tool results already render generically.
- tRPC routes — no changes. Chat flow is the same.
- Auth, database, project management — untouched.
- Existing tools (execute_sql, read, grep, list, search, display_chart) — untouched.
- RULES.md — still works as before, complemented by structured business_rules.yml.

### Agent decision flow (new)

```
User question arrives
        |
        v
  System prompt includes:
  - Database connections (existing)
  - RULES.md (existing)
  - Available metrics/dimensions from semantic_model.yml (NEW)
  - Critical business rules from business_rules.yml (NEW)
        |
        v
  LLM decides which tool to use:
        |
        +-- Question maps to a defined metric?
        |     --> query_metrics tool
        |
        +-- Question needs ad-hoc exploration?
        |     --> execute_sql tool (existing behavior)
        |
        +-- Question asks "why" or needs interpretation?
        |     --> get_business_context tool
        |
        +-- Question needs file/doc lookup?
        |     --> read, grep, list, search tools (existing)
        |
        v
  Results returned to LLM
        |
        v
  LLM generates answer with:
  - Data from semantic layer or raw SQL
  - Business context and caveats from rules engine
  - Charts if applicable
```

### File inventory (new files only)

```
cli/dazense_core/semantic/__init__.py        # Module init
cli/dazense_core/semantic/model.py           # YAML parser (~100 lines)
cli/dazense_core/semantic/compiler.py        # Ibis query builder (~200 lines)
cli/dazense_core/semantic/validator.py       # Schema validation (~100 lines)
cli/dazense_core/rules/__init__.py           # Module init
cli/dazense_core/rules/loader.py             # YAML parser (~50 lines)
cli/dazense_core/rules/engine.py             # Rule matching (~100 lines)
apps/backend/src/agents/tools/query-metrics.ts    # Agent tool (~40 lines)
apps/backend/src/agents/tools/get-business-context.ts  # Agent tool (~40 lines)

Total: ~650 lines of new code
```

### Dependencies (new)

**None.** Everything uses existing dependencies:

- Ibis (already in cli/pyproject.toml)
- PyYAML (already in cli/pyproject.toml)
- FastAPI/uvicorn (already running)
- Vercel AI SDK (already in backend)
