import ibis
import pytest

from nao_core.config.databases.duckdb import DuckDBConfig
from nao_core.semantic.engine import SemanticEngine
from nao_core.semantic.models import SemanticModel


@pytest.fixture()
def duckdb_with_data():
    """Create an in-memory DuckDB with test data."""
    conn = ibis.duckdb.connect()
    conn.raw_sql("""
        CREATE TABLE main.customers (
            customer_id INTEGER,
            first_name VARCHAR,
            last_name VARCHAR
        )
    """)
    conn.raw_sql("""
        INSERT INTO main.customers VALUES
        (1, 'Alice', 'Smith'),
        (2, 'Bob', 'Jones'),
        (3, 'Charlie', 'Brown')
    """)
    conn.raw_sql("""
        CREATE TABLE main.orders (
            order_id INTEGER,
            user_id INTEGER,
            status VARCHAR,
            amount DECIMAL(10,2),
            order_date DATE
        )
    """)
    conn.raw_sql("""
        INSERT INTO main.orders VALUES
        (1, 1, 'completed', 100.00, '2024-01-01'),
        (2, 1, 'completed', 50.00, '2024-01-02'),
        (3, 2, 'cancelled', 75.00, '2024-01-03'),
        (4, 3, 'completed', 200.00, '2024-01-04'),
        (5, 2, 'completed', 125.00, '2024-01-05')
    """)
    return conn


@pytest.fixture()
def semantic_model():
    return SemanticModel.model_validate(
        {
            "models": {
                "customers": {
                    "table": "customers",
                    "schema": "main",
                    "dimensions": {
                        "customer_id": {"column": "customer_id"},
                        "first_name": {"column": "first_name"},
                    },
                    "measures": {"customer_count": {"type": "count"}},
                },
                "orders": {
                    "table": "orders",
                    "schema": "main",
                    "time_dimension": "order_date",
                    "dimensions": {
                        "status": {"column": "status"},
                    },
                    "measures": {
                        "order_count": {"type": "count"},
                        "total_amount": {"type": "sum", "column": "amount"},
                        "avg_order_value": {"type": "avg", "column": "amount"},
                    },
                    "joins": {
                        "customer": {
                            "to_model": "customers",
                            "foreign_key": "user_id",
                            "related_key": "customer_id",
                            "type": "many_to_one",
                        }
                    },
                },
            }
        }
    )


@pytest.fixture()
def engine(semantic_model, duckdb_with_data, monkeypatch):
    """Create engine with a mock DuckDB config that returns our test connection."""
    db_config = DuckDBConfig(name="test-db", path=":memory:")
    engine = SemanticEngine(semantic_model, [db_config])
    # Override the connection to use our pre-populated one
    engine._connections["test-db"] = duckdb_with_data
    return engine


def test_simple_count(engine):
    result = engine.query("orders", measures=["order_count"])
    assert len(result) == 1
    assert result[0]["order_count"] == 5


def test_sum_measure(engine):
    result = engine.query("orders", measures=["total_amount"])
    assert len(result) == 1
    assert result[0]["total_amount"] == 550.00


def test_group_by_dimension(engine):
    result = engine.query("orders", measures=["order_count"], dimensions=["status"])
    assert len(result) == 2
    by_status = {row["status"]: row["order_count"] for row in result}
    assert by_status["completed"] == 4
    assert by_status["cancelled"] == 1


def test_filter(engine):
    result = engine.query(
        "orders",
        measures=["total_amount"],
        filters=[{"column": "status", "operator": "eq", "value": "completed"}],
    )
    assert result[0]["total_amount"] == 475.00


def test_filter_not_in(engine):
    result = engine.query(
        "orders",
        measures=["order_count"],
        filters=[{"column": "status", "operator": "not_in", "value": ["cancelled"]}],
    )
    assert result[0]["order_count"] == 4


def test_order_by(engine):
    result = engine.query(
        "orders",
        measures=["order_count"],
        dimensions=["status"],
        order_by=[{"column": "order_count", "ascending": False}],
    )
    assert result[0]["order_count"] >= result[1]["order_count"]


def test_limit(engine):
    result = engine.query(
        "orders",
        measures=["order_count"],
        dimensions=["status"],
        limit=1,
    )
    assert len(result) == 1


def test_join_dimension(engine):
    result = engine.query(
        "orders",
        measures=["order_count"],
        dimensions=["customer.first_name"],
    )
    assert len(result) == 3
    names = {row["customer_first_name"] for row in result}
    assert "Alice" in names
    assert "Bob" in names


def test_model_not_found(engine):
    with pytest.raises(ValueError, match="Model 'nonexistent' not found"):
        engine.query("nonexistent", measures=["order_count"])


def test_measure_not_found(engine):
    with pytest.raises(ValueError, match="Measure 'bad_measure' not found"):
        engine.query("orders", measures=["bad_measure"])


def test_dimension_not_found(engine):
    with pytest.raises(ValueError, match="Dimension 'bad_dim' not found"):
        engine.query("orders", measures=["order_count"], dimensions=["bad_dim"])


def test_get_model_info(engine):
    info = engine.get_model_info("orders")
    assert info["name"] == "orders"
    assert info["table"] == "orders"
    assert "status" in info["dimensions"]
    assert "order_count" in info["measures"]
    assert "customer" in info["joins"]


def test_avg_measure(engine):
    result = engine.query("orders", measures=["avg_order_value"])
    assert len(result) == 1
    assert result[0]["avg_order_value"] == pytest.approx(110.0)
