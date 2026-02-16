from textwrap import dedent

import pytest

from nao_core.semantic.models import (
    AggregationType,
    JoinType,
    Measure,
    SemanticModel,
)


def test_parse_basic_model():
    data = {
        "models": {
            "orders": {
                "table": "orders",
                "schema": "main",
                "dimensions": {
                    "status": {"column": "status"},
                },
                "measures": {
                    "order_count": {"type": "count"},
                    "total_amount": {"type": "sum", "column": "amount"},
                },
            }
        }
    }
    model = SemanticModel.model_validate(data)
    assert "orders" in model.models
    assert model.models["orders"].table == "orders"
    assert model.models["orders"].schema_name == "main"
    assert model.models["orders"].dimensions["status"].column == "status"
    assert model.models["orders"].measures["order_count"].type == AggregationType.COUNT
    assert model.models["orders"].measures["total_amount"].column == "amount"


def test_parse_with_joins():
    data = {
        "models": {
            "orders": {
                "table": "orders",
                "schema": "main",
                "dimensions": {},
                "measures": {"order_count": {"type": "count"}},
                "joins": {
                    "customer": {
                        "to_model": "customers",
                        "foreign_key": "user_id",
                        "related_key": "customer_id",
                        "type": "many_to_one",
                    }
                },
            }
        }
    }
    model = SemanticModel.model_validate(data)
    join = model.models["orders"].joins["customer"]
    assert join.to_model == "customers"
    assert join.foreign_key == "user_id"
    assert join.type == JoinType.MANY_TO_ONE


def test_measure_requires_column_for_non_count():
    with pytest.raises(ValueError, match="requires a 'column' field"):
        Measure(type=AggregationType.SUM)


def test_count_measure_no_column_required():
    measure = Measure(type=AggregationType.COUNT)
    assert measure.column is None


def test_list_models():
    data = {
        "models": {
            "orders": {"table": "orders", "schema": "main", "measures": {"c": {"type": "count"}}},
            "customers": {"table": "customers", "schema": "main", "measures": {"c": {"type": "count"}}},
        }
    }
    model = SemanticModel.model_validate(data)
    assert sorted(model.list_models()) == ["customers", "orders"]


def test_get_model():
    data = {
        "models": {
            "orders": {"table": "orders", "schema": "main", "measures": {"c": {"type": "count"}}},
        }
    }
    model = SemanticModel.model_validate(data)
    assert model.get_model("orders") is not None
    assert model.get_model("nonexistent") is None


def test_load_from_yaml(tmp_path):
    semantics_dir = tmp_path / "semantics"
    semantics_dir.mkdir()
    yaml_content = dedent("""\
        models:
          orders:
            table: orders
            schema: main
            dimensions:
              status:
                column: status
            measures:
              order_count:
                type: count
    """)
    (semantics_dir / "semantic_model.yml").write_text(yaml_content)

    model = SemanticModel.load(tmp_path)
    assert model is not None
    assert "orders" in model.models


def test_load_returns_none_when_missing(tmp_path):
    assert SemanticModel.load(tmp_path) is None


def test_all_aggregation_types():
    for agg_type in AggregationType:
        if agg_type == AggregationType.COUNT:
            measure = Measure(type=agg_type)
            assert measure.column is None
        else:
            measure = Measure(type=agg_type, column="value")
            assert measure.column == "value"
