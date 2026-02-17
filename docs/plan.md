# dazense+ : Commercialization Plan

## Vision

Transform dazense from an open-source SQL generation tool into a **production-ready analytics reasoning platform** by integrating a semantic layer and business rules engine, then commercializing via an open-core model with a hosted cloud offering.

---

## Context

### What dazense is today

dazense is an open-source framework for building analytics agents. Users define a project context (databases, metadata, docs, tools) via a Python CLI, then deploy a chat UI where business users ask questions in natural language and get data insights.

**Current stack:** Python CLI (dazense-core) + TypeScript backend (Fastify/tRPC/Bun) + React frontend (TanStack/Shadcn) + FastAPI tools server.

### The gap

dazense's agent writes **raw SQL from scratch every time**. It reads schema markdown files, infers table relationships, and generates queries. This works for simple cases but has real failure modes:

- **Inconsistent answers** — same question, different SQL, different numbers
- **Wrong joins** — LLM guesses relationships from column names
- **No metric governance** — "revenue" has no single definition
- **No business context** — agent can produce correct numbers with misleading interpretations
- **Token waste** — agent reads files and reasons about schema on every query

### The opportunity

Integrate a **semantic layer** (consistent metric definitions) and **business rules engine** (domain knowledge and caveats) into dazense. This IP comes from the datazense project, which demonstrated a 3-layer metadata architecture (Technical/Semantic/Ontology) for AI-powered analytics.

---

## Plan

### Phase 1: Semantic Layer

**Goal:** Users define metrics and dimensions in YAML. The agent calls `query_metrics()` instead of writing raw SQL for known metrics.

**What to build:**

1. **YAML-to-Ibis translator** (~300-500 lines of Python)
    - Location: `cli/dazense_core/semantic/` (new module)
    - Parses a `semantic_model.yml` file from the project folder
    - Resolves table references, joins, and aggregations
    - Translates metric queries into Ibis expressions
    - Ibis compiles to the target SQL dialect (DuckDB, Postgres, BigQuery, Snowflake, etc.)
    - No external dependency — Ibis is already in dazense's stack

2. **New FastAPI endpoint** (`/query_metrics`)
    - Location: `apps/backend/fastapi/main.py` (extend existing)
    - Accepts: `{ measures: [...], dimensions: [...], filters: {...}, limit: N }`
    - Loads semantic model from project folder
    - Executes via the Ibis translator
    - Returns: `{ data: [...], columns: [...], row_count: N }`

3. **New agent tool** (`query-metrics.ts`)
    - Location: `apps/backend/src/agents/tools/query-metrics.ts`
    - Same HTTP pattern as `execute-sql.ts` — calls FastAPI endpoint
    - Input schema exposes available measures and dimensions

4. **System prompt updates**
    - Location: `apps/backend/src/components/system-prompt.tsx`
    - Inject available metrics/dimensions from the semantic model
    - Instruct agent: prefer `query_metrics` for defined metrics, fall back to `execute_sql` for ad-hoc queries

5. **CLI awareness**
    - `dazense sync` validates the semantic model if present
    - `dazense init` optionally scaffolds a starter `semantic_model.yml`

**Semantic model format** (per project):

```yaml
# semantic_model.yml
models:
    orders:
        table: orders
        time_dimension: order_date
        dimensions:
            status: _.status
            customer_id: _.customer_id
        measures:
            order_count: _.count()
            total_amount: _.amount.sum()
            avg_amount: _.amount.mean()
        joins:
            customer:
                model: customers
                type: one
                with: _.customer_id

    customers:
        table: customers
        primary_key: customer_id
        dimensions:
            customer_id: _.customer_id
            first_name: _.first_name
            last_name: _.last_name
```

**Key design decisions:**

- Semantic model is **optional** — projects without it work exactly as today
- Agent uses both tools — `query_metrics` for governed metrics, `execute_sql` for exploration
- Ibis handles dialect translation — one YAML works across all supported databases
- No boring-semantic-layer dependency — owned code, full control

### Phase 2: Business Rules Engine

**Goal:** Attach business context, caveats, and classification logic to data concepts so the agent provides insight, not just numbers.

**What to build:**

1. **Business rules YAML format**
    - Location: `business_rules.yml` in the project folder (or a section in `semantic_model.yml`)
    - Defines: rules, caveats, classifications, interpretation guidance

2. **New FastAPI endpoint** (`/get_business_context`)
    - Accepts: `{ concept: "tips", context: "cash_payments" }`
    - Returns relevant rules, caveats, and guidance

3. **New agent tool** (`get-business-context.ts`)
    - Agent calls this when interpreting results or answering "why" questions

4. **System prompt injection**
    - Critical rules injected directly into the system prompt
    - Less critical rules available via tool call

**Business rules format:**

```yaml
# business_rules.yml
rules:
    - name: cash_tips_not_recorded
      applies_to: [tip_amount, tips]
      severity: critical
      description: Cash tips are NOT recorded in the data
      guidance: Exclude cash payments from any tip analysis

    - name: jfk_flat_rate
      applies_to: [fare_amount, airport]
      severity: info
      description: JFK airport uses a flat $52 rate
      guidance: Do not compare JFK fares with metered trips

classifications:
    trip_type:
        airport:
            rule: "rate_code IN (2, 3) OR zone_type = 'Airport'"
            characteristics:
                expected_tip_rate: '15-20%'
        commute:
            rule: 'weekday AND hour BETWEEN 7 AND 9'
            characteristics:
                recurring: true
```

**Key design decisions:**

- Start simple — YAML rules, no RDF/SPARQL, no rdflib
- Critical rules go in system prompt (always visible to agent)
- Detailed rules available via tool (on-demand)
- Complements RULES.md — structured rules for the engine, free-form rules for human instructions

### Phase 3: Hosted Cloud

**Goal:** Deploy dazense as a hosted service. Users sign up, connect a database, define metrics, and chat.

**What to build:**

1. **Multi-tenant infrastructure** — isolated projects per team/org
2. **Onboarding flow** — connect database, auto-discover schema, suggest metrics
3. **Billing** — per-seat pricing ($20-50/seat/month)
4. **Admin dashboard** — usage analytics, cost tracking, user management

**This phase is product/infra work, not covered in the architecture document.**

### Phase 4: Enterprise Features (Paid Tier)

- SSO (SAML/OIDC)
- Audit logs
- Role-based access to metrics and databases
- Scheduled reports and alerts
- Slack/Teams integration (already partially built)
- On-premise deployment support
- SLA and priority support

---

## Commercialization Model

### Open-core

| Tier           | Price             | Features                                                                    |
| -------------- | ----------------- | --------------------------------------------------------------------------- |
| **Community**  | Free              | CLI, single-user chat, raw SQL agent, basic auth                            |
| **Team**       | $20-50/seat/month | Semantic layer, business rules, shared chat history, usage analytics, Slack |
| **Enterprise** | Custom            | SSO, audit logs, RBAC, on-prem, SLA, scheduled reports                      |

### Revenue path

1. **Cloud hosted** — primary revenue driver, lowest friction
2. **Enterprise licenses** — for companies that need on-prem
3. **Support contracts** — for teams that need guaranteed response times

### Competitive edge

The semantic layer + business rules engine is the moat. Open-source dazense writes raw SQL (anyone can do that). Paid dazense delivers **governed, consistent, context-aware analytics** — that's what enterprises pay for.

---

## Risks

| Risk                                          | Mitigation                                                          |
| --------------------------------------------- | ------------------------------------------------------------------- |
| Semantic model is hard for users to write     | Auto-generate starter model from database schema during `dazense sync`  |
| Agent picks wrong tool (semantic vs raw SQL)  | Careful prompt engineering + fallback logic                         |
| Ibis doesn't support a target database        | Ibis supports 20+ backends — unlikely, but can add raw SQL fallback |
| boring-semantic-layer was simpler than custom | Custom code is ~300-500 lines, well within maintenance budget       |
| Cloud hosting costs                           | Start with single-region, scale based on revenue                    |
