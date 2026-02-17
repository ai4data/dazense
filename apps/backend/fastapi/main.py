import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import numpy as np
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

cli_path = Path(__file__).parent.parent.parent / "cli"
sys.path.insert(0, str(cli_path))

from dazense_core.config import DazenseConfig, DazenseConfigError
from dazense_core.context import get_context_provider
from dazense_core.rules import BusinessRules
from dazense_core.semantic import SemanticEngine, SemanticModel

port = int(os.environ.get("PORT", 8005))

# Global scheduler instance
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - setup scheduler on startup."""
    global scheduler

    # Setup periodic refresh if configured
    refresh_schedule = os.environ.get("DAZENSE_REFRESH_SCHEDULE")
    if refresh_schedule:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = AsyncIOScheduler()

        try:
            trigger = CronTrigger.from_crontab(refresh_schedule)
            scheduler.add_job(
                _refresh_context_task,
                trigger,
                id="context_refresh",
                name="Periodic context refresh",
            )
            scheduler.start()
            print(f"[Scheduler] Periodic refresh enabled: {refresh_schedule}")
        except ValueError as e:
            print(f"[Scheduler] Invalid cron expression '{refresh_schedule}': {e}")

    yield

    # Shutdown scheduler
    if scheduler:
        scheduler.shutdown(wait=False)


async def _refresh_context_task():
    """Background task for scheduled context refresh."""
    try:
        provider = get_context_provider()
        updated = provider.refresh()
        if updated:
            print(f"[Scheduler] Context refreshed at {datetime.now().isoformat()}")
        else:
            print(
                f"[Scheduler] Context already up-to-date at {datetime.now().isoformat()}"
            )
    except Exception as e:
        print(f"[Scheduler] Failed to refresh context: {e}")


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request/Response Models
# =============================================================================


class ExecuteSQLRequest(BaseModel):
    sql: str
    dazense_project_folder: str
    database_id: str | None = None


class ExecuteSQLResponse(BaseModel):
    data: list[dict]
    row_count: int
    columns: list[str]


class RefreshResponse(BaseModel):
    status: str
    updated: bool
    message: str


class QueryMetricsRequest(BaseModel):
    dazense_project_folder: str
    model_name: str
    measures: list[str]
    dimensions: list[str] = []
    filters: list[dict] = []
    order_by: list[dict] = []
    limit: int | None = None
    database_id: str | None = None


class QueryMetricsResponse(BaseModel):
    data: list[dict]
    row_count: int
    columns: list[str]
    model_name: str
    measures: list[str]
    dimensions: list[str]


class BusinessContextRequest(BaseModel):
    dazense_project_folder: str
    category: str | None = None
    concepts: list[str] = []


class BusinessContextResponse(BaseModel):
    rules: list[dict]
    categories: list[str]


class ClassifyRequest(BaseModel):
    dazense_project_folder: str
    name: str | None = None
    tags: list[str] = []


class ClassifyResponse(BaseModel):
    classifications: list[dict]
    available_names: list[str]


class HealthResponse(BaseModel):
    status: str
    context_source: str
    context_initialized: bool
    refresh_schedule: str | None


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with context status."""
    try:
        provider = get_context_provider()
        context_source = os.environ.get("DAZENSE_CONTEXT_SOURCE", "local")
        return HealthResponse(
            status="ok",
            context_source=context_source,
            context_initialized=provider.is_initialized(),
            refresh_schedule=os.environ.get("DAZENSE_REFRESH_SCHEDULE"),
        )
    except Exception:
        return HealthResponse(
            status="error",
            context_source=os.environ.get("DAZENSE_CONTEXT_SOURCE", "local"),
            context_initialized=False,
            refresh_schedule=os.environ.get("DAZENSE_REFRESH_SCHEDULE"),
        )


@app.post("/api/refresh", response_model=RefreshResponse)
async def refresh_context():
    """Trigger a context refresh (git pull if using git source).

    This endpoint can be called by:
    - CI/CD pipelines after pushing new context
    - Webhooks when data schemas change
    - Manual triggers for immediate updates
    """
    try:
        provider = get_context_provider()
        updated = provider.refresh()

        if updated:
            return RefreshResponse(
                status="ok",
                updated=True,
                message="Context updated successfully",
            )
        else:
            return RefreshResponse(
                status="ok",
                updated=False,
                message="Context already up-to-date",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh context: {str(e)}",
        )


@app.post("/execute_sql", response_model=ExecuteSQLResponse)
async def execute_sql(request: ExecuteSQLRequest):
    try:
        # Load the dazense config from the project folder
        project_path = Path(request.dazense_project_folder)
        os.chdir(project_path)
        config = DazenseConfig.try_load(project_path, raise_on_error=True)
        assert config is not None

        if len(config.databases) == 0:
            raise HTTPException(
                status_code=400,
                detail="No databases configured in dazense_config.yaml",
            )

        # Determine which database to use
        if len(config.databases) == 1:
            db_config = config.databases[0]
        elif request.database_id:
            # Find the database by name
            db_config = next(
                (db for db in config.databases if db.name == request.database_id),
                None,
            )
            if db_config is None:
                available_databases = [db.name for db in config.databases]
                raise HTTPException(
                    status_code=400,
                    detail={
                        "message": f"Database '{request.database_id}' not found",
                        "available_databases": available_databases,
                    },
                )
        else:
            # Multiple databases and no database_id specified
            available_databases = [db.name for db in config.databases]
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Multiple databases configured. Please specify database_id.",
                    "available_databases": available_databases,
                },
            )

        df = db_config.execute_sql(request.sql)

        def convert_value(v):
            if isinstance(v, (np.integer,)):
                return int(v)
            if isinstance(v, (np.floating,)):
                return float(v)
            if isinstance(v, np.ndarray):
                return v.tolist()
            if hasattr(v, "item"):  # numpy scalar
                return v.item()
            return v

        data = [
            {k: convert_value(v) for k, v in row.items()}
            for row in df.to_dict(orient="records")
        ]

        return ExecuteSQLResponse(
            data=data,
            row_count=len(data),
            columns=[str(c) for c in df.columns.tolist()],
        )
    except HTTPException:
        raise
    except DazenseConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query_metrics", response_model=QueryMetricsResponse)
async def query_metrics(request: QueryMetricsRequest):
    try:
        project_path = Path(request.dazense_project_folder)
        os.chdir(project_path)

        semantic_model = SemanticModel.load(project_path)
        if semantic_model is None:
            raise HTTPException(
                status_code=400,
                detail="No semantic_model.yml found in semantics/ folder",
            )

        config = DazenseConfig.try_load(project_path, raise_on_error=True)
        assert config is not None

        engine = SemanticEngine(semantic_model, config.databases)
        rows = engine.query(
            model_name=request.model_name,
            measures=request.measures,
            dimensions=request.dimensions,
            filters=request.filters,
            order_by=request.order_by,
            limit=request.limit,
        )

        columns = list(rows[0].keys()) if rows else request.dimensions + request.measures

        return QueryMetricsResponse(
            data=rows,
            row_count=len(rows),
            columns=columns,
            model_name=request.model_name,
            measures=request.measures,
            dimensions=request.dimensions,
        )
    except HTTPException:
        raise
    except DazenseConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/business_context", response_model=BusinessContextResponse)
async def business_context(request: BusinessContextRequest):
    try:
        project_path = Path(request.dazense_project_folder)

        business_rules = BusinessRules.load(project_path)
        if business_rules is None:
            raise HTTPException(
                status_code=400,
                detail="No business_rules.yml found in semantics/ folder",
            )

        if request.category:
            rules = business_rules.filter_by_category(request.category)
        elif request.concepts:
            rules = business_rules.filter_by_concept(request.concepts)
        else:
            rules = business_rules.rules

        return BusinessContextResponse(
            rules=[r.model_dump() for r in rules],
            categories=business_rules.get_categories(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/classify", response_model=ClassifyResponse)
async def classify(request: ClassifyRequest):
    try:
        project_path = Path(request.dazense_project_folder)

        business_rules = BusinessRules.load(project_path)
        if business_rules is None:
            raise HTTPException(
                status_code=400,
                detail="No business_rules.yml found in semantics/ folder",
            )

        if request.name:
            classification = business_rules.get_classification(request.name)
            classifications = [classification] if classification else []
        elif request.tags:
            classifications = business_rules.filter_classifications_by_tags(
                request.tags
            )
        else:
            classifications = business_rules.classifications

        return ClassifyResponse(
            classifications=[c.model_dump() for c in classifications],
            available_names=business_rules.get_classification_names(),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    dazense_project_folder = os.getenv("DAZENSE_DEFAULT_PROJECT_PATH")
    if dazense_project_folder:
        os.chdir(dazense_project_folder)
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
