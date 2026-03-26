import json
from jsonschema import validate, ValidationError

from src.schema import (
    SchemaSpec, OutputSpec, EntitySpec, RelationshipSpec,
    AttributeSpec, Distribution
)
from src.dsl_schema import JSON_SCHEMA
from src.validators import semantic_validate


def _parse_distribution(dist_data: dict) -> Distribution:
    kind = dist_data["kind"]
    params = {k: v for k, v in dist_data.items() if k != "kind"}
    return Distribution(kind=kind, params=params)


def _parse_attribute(attr_data: dict) -> AttributeSpec:
    distribution = None
    if "distribution" in attr_data:
        distribution = _parse_distribution(attr_data["distribution"])

    return AttributeSpec(
        name=attr_data["name"],
        type=attr_data["type"],
        role=attr_data.get("role"),
        unique=attr_data.get("unique", False),
        generator=attr_data.get("generator"),
        distribution=distribution
    )


def parse_schema(path: str) -> SchemaSpec:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        validate(instance=data, schema=JSON_SCHEMA)
    except ValidationError as e:
        raise ValueError(
            f"Invalid input schema:\n  {e.message}\n  Path: {list(e.path)}"
        )

    output = OutputSpec(
        formats=data["output"]["formats"],
        directory=data["output"]["directory"]
    )

    entities = [
        EntitySpec(
            name=e["name"],
            rows=e["rows"],
            attributes=[_parse_attribute(a) for a in e["attributes"]]
        )
        for e in data["entities"]
    ]

    relationships = [
        RelationshipSpec(
            name=r["name"],
            type=r["type"],
            between=r["between"],
            rows=r["rows"],
            participation=r["participation"],
            attributes=[_parse_attribute(a) for a in r.get("attributes", [])]
        )
        for r in data["relationships"]
    ]

    spec = SchemaSpec(
        schema_name=data["schema_name"],
        output=output,
        entities=entities,
        relationships=relationships
    )

    semantic_validate(spec)
    return spec
