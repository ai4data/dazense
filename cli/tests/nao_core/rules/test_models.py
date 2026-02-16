from textwrap import dedent

from nao_core.rules.models import BusinessRule, BusinessRules, Classification


def test_parse_rules():
    data = {
        "rules": [
            {
                "name": "test_rule",
                "category": "data_quality",
                "severity": "critical",
                "applies_to": ["tip_amount"],
                "description": "Test description",
                "guidance": "Test guidance",
            }
        ]
    }
    rules = BusinessRules.model_validate(data)
    assert len(rules.rules) == 1
    assert rules.rules[0].name == "test_rule"
    assert rules.rules[0].severity == "critical"


def test_filter_by_category():
    data = {
        "rules": [
            {
                "name": "rule1",
                "category": "metrics",
                "description": "D1",
                "guidance": "G1",
            },
            {
                "name": "rule2",
                "category": "data_quality",
                "description": "D2",
                "guidance": "G2",
            },
            {
                "name": "rule3",
                "category": "metrics",
                "description": "D3",
                "guidance": "G3",
            },
        ]
    }
    rules = BusinessRules.model_validate(data)
    metrics_rules = rules.filter_by_category("metrics")
    assert len(metrics_rules) == 2
    assert all(r.category == "metrics" for r in metrics_rules)


def test_filter_by_concept():
    data = {
        "rules": [
            {
                "name": "rule1",
                "category": "metrics",
                "applies_to": ["orders.total_revenue"],
                "description": "D1",
                "guidance": "G1",
            },
            {
                "name": "rule2",
                "category": "data_quality",
                "applies_to": ["tip_amount"],
                "description": "D2",
                "guidance": "G2",
            },
        ]
    }
    rules = BusinessRules.model_validate(data)
    matched = rules.filter_by_concept(["tip_amount"])
    assert len(matched) == 1
    assert matched[0].name == "rule2"


def test_get_categories():
    data = {
        "rules": [
            {"name": "r1", "category": "metrics", "description": "D", "guidance": "G"},
            {"name": "r2", "category": "data_quality", "description": "D", "guidance": "G"},
            {"name": "r3", "category": "metrics", "description": "D", "guidance": "G"},
        ]
    }
    rules = BusinessRules.model_validate(data)
    categories = rules.get_categories()
    assert categories == ["data_quality", "metrics"]


def test_load_from_yaml(tmp_path):
    semantics_dir = tmp_path / "semantics"
    semantics_dir.mkdir()
    yaml_content = dedent("""\
        rules:
          - name: test_rule
            category: metrics
            severity: critical
            applies_to: [revenue]
            description: Test
            guidance: Do this
    """)
    (semantics_dir / "business_rules.yml").write_text(yaml_content)

    rules = BusinessRules.load(tmp_path)
    assert rules is not None
    assert len(rules.rules) == 1


def test_load_returns_none_when_missing(tmp_path):
    assert BusinessRules.load(tmp_path) is None


def test_default_severity():
    rule = BusinessRule(
        name="test",
        category="metrics",
        description="D",
        guidance="G",
    )
    assert rule.severity == "info"


def test_parse_classification():
    c = Classification(
        name="airport_trip",
        description="Trip to airport",
        condition="ratecode_id IN (2, 3)",
        tags=["zone", "fare"],
        characteristics={"flat_rate": "$52"},
    )
    assert c.name == "airport_trip"
    assert c.tags == ["zone", "fare"]
    assert c.characteristics["flat_rate"] == "$52"


def test_classification_defaults():
    c = Classification(
        name="test",
        description="Test",
        condition="x = 1",
    )
    assert c.tags == []
    assert c.characteristics == {}


def test_parse_classifications_as_list():
    data = {
        "rules": [
            {"name": "r1", "category": "metrics", "description": "D", "guidance": "G"},
        ],
        "classifications": [
            {
                "name": "airport_trip",
                "description": "Airport trip",
                "condition": "ratecode_id IN (2, 3)",
                "tags": ["zone"],
                "characteristics": {"flat_rate": "$52"},
            }
        ],
    }
    rules = BusinessRules.model_validate(data)
    assert len(rules.classifications) == 1
    assert rules.classifications[0].name == "airport_trip"


def test_get_classification():
    data = {
        "rules": [],
        "classifications": [
            {"name": "airport", "description": "Airport", "condition": "x = 1"},
            {"name": "commute", "description": "Commute", "condition": "y = 2"},
        ],
    }
    rules = BusinessRules.model_validate(data)
    classification = rules.get_classification("airport")
    assert classification is not None
    assert classification.name == "airport"
    assert rules.get_classification("nonexistent") is None


def test_filter_classifications_by_tags():
    data = {
        "rules": [],
        "classifications": [
            {"name": "c1", "description": "D1", "condition": "x", "tags": ["zone", "fare"]},
            {"name": "c2", "description": "D2", "condition": "y", "tags": ["time"]},
            {"name": "c3", "description": "D3", "condition": "z", "tags": ["fare", "tip"]},
        ],
    }
    rules = BusinessRules.model_validate(data)
    matched = rules.filter_classifications_by_tags(["fare"])
    assert len(matched) == 2
    assert {c.name for c in matched} == {"c1", "c3"}


def test_get_classification_names():
    data = {
        "rules": [],
        "classifications": [
            {"name": "airport", "description": "D1", "condition": "x"},
            {"name": "commute", "description": "D2", "condition": "y"},
        ],
    }
    rules = BusinessRules.model_validate(data)
    assert rules.get_classification_names() == ["airport", "commute"]


def test_load_classifications_from_yaml_dict_format(tmp_path):
    semantics_dir = tmp_path / "semantics"
    semantics_dir.mkdir()
    yaml_content = dedent("""\
        rules:
          - name: test_rule
            category: metrics
            description: Test
            guidance: Do this

        classifications:
          airport_trip:
            description: "Trip to airport"
            condition: "ratecode_id IN (2, 3)"
            tags: [zone, fare]
            characteristics:
              flat_rate: "$52"
    """)
    (semantics_dir / "business_rules.yml").write_text(yaml_content)

    rules = BusinessRules.load(tmp_path)
    assert rules is not None
    assert len(rules.classifications) == 1
    assert rules.classifications[0].name == "airport_trip"
    assert rules.classifications[0].characteristics["flat_rate"] == "$52"


def test_no_classifications_defaults_empty():
    data = {
        "rules": [
            {"name": "r1", "category": "metrics", "description": "D", "guidance": "G"},
        ]
    }
    rules = BusinessRules.model_validate(data)
    assert rules.classifications == []
    assert rules.get_classification_names() == []
