import csv
import inflect
from typing import cast, Any
from pathlib import Path
from .schema import SchemaSpec, EntitySpec, RelationshipSpec
from .data_generator import should_use_table

DSL_TO_PG_TYPE = {
    "int":         "INTEGER",
    "pyint":       "INTEGER",
    "port_number": "INTEGER",
    "float":       "NUMERIC",
    "pyfloat":     "NUMERIC",
    "pydecimal":   "NUMERIC",
    "unix_time":   "NUMERIC",
    "boolean":     "BOOLEAN",
    "pybool":      "BOOLEAN",
    "uuid4":       "UUID",
    "uuid":        "UUID",
    "date":                    "DATE",
    "date_of_birth":           "DATE",
    "date_object":             "DATE",
    "date_this_year":          "DATE",
    "date_this_month":         "DATE",
    "date_this_decade":        "DATE",
    "date_this_century":       "DATE",
    "date_between":            "DATE",
    "date_between_dates":      "DATE",
    "future_date":             "DATE",
    "past_date":               "DATE",
    "date_time":               "TIMESTAMP",
    "date_time_ad":            "TIMESTAMP",
    "date_time_between":       "TIMESTAMP",
    "date_time_between_dates": "TIMESTAMP",
    "date_time_this_century":  "TIMESTAMP",
    "date_time_this_decade":   "TIMESTAMP",
    "date_time_this_month":    "TIMESTAMP",
    "date_time_this_year":     "TIMESTAMP",
    "future_datetime":         "TIMESTAMP",
    "past_datetime":           "TIMESTAMP",
    "time":                    "TIME",
    "time_object":             "TIME",
}

_inflect = inflect.engine()

def _pluralize(name: str) -> str:
    plural_word = _inflect.plural(cast(Any, name.lower()))
    return str(plural_word)


def write_csv(entity_name: str, rows: list[dict], directory: str):
    if not rows:
        return
    
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    filepath = dir_path / f"{entity_name}.csv"

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  [CSV] Written {len(rows)} rows to {filepath.as_posix()}")


def _sql_value(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        return "TRUE" if val else "FALSE"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (dict, list, tuple, set)):
        raise ValueError(
            f"Value '{val}' is a complex Python object and cannot be serialized to SQL. "
            "Avoid using faker types like pydict, pylist, pytuple, pyset, pyiterable for SQL output."
        )
    escaped = str(val).replace("'", "''")
    return f"'{escaped}'"


def _pg_type(dsl_type: str) -> str:
    return DSL_TO_PG_TYPE.get(dsl_type, "TEXT")


def _build_create_table(entity: EntitySpec, spec:SchemaSpec) -> str:
    table = _pluralize(entity.name)
    lines = []

    for attr in entity.attributes:
        pg_type = _pg_type(attr.type)
        lines.append(f"    {attr.name} {pg_type} NOT NULL")
    
    try:
        pk = entity.primary_key()
        lines.append(f"    PRIMARY KEY ({pk.name})")
    except ValueError:
        pass

    for attr in entity.attributes:
        if attr.unique and attr.role != "primary_key":
            lines.append(f"    UNIQUE ({attr.name})")
    
    for rel in spec.relationships:
        entity_a, entity_b = rel.between
        if entity_b == entity.name and not should_use_table(rel):
            pk_a = spec.entity_map()[entity_a].primary_key()
            fk_col_name = f"{pk_a.name}"
            
            # NOT NULL for total participation
            lines.append(f"    {fk_col_name} {_pg_type(pk_a.type)} {'NOT NULL' if rel.participation.get(entity_b) == 'total' else ''}")

            # Add the UNIQUE constraint if this is a 1:1 relationship
            if rel.type == "one_to_one":
                lines.append(f"    UNIQUE ({fk_col_name})")

            lines.append(f"    FOREIGN KEY ({fk_col_name}) REFERENCES {_pluralize(entity_a)}({pk_a.name})")

    body = ",\n".join(lines)
    return (
        f"-- Table: {table}\n"
        f"CREATE TABLE IF NOT EXISTS {table} (\n"
        f"{body}\n"
        f");\n"
    )


def _topological_sort(spec: SchemaSpec) -> list[str]:
    """
    Orders entities based on Foreign Key dependencies using Kahn's Algorithm.
    Ensures parent tables are created/inserted before child tables.
    """
    entity_names = [e.name for e in spec.entities]

    dependencies: dict[str, set[str]] = {name: set() for name in entity_names}
 
    for rel in spec.relationships:
        if not should_use_table(rel):
            # FK is embedded in entity_b → entity_b depends on entity_a
            entity_a, entity_b = rel.between
            if entity_a in dependencies and entity_b in dependencies:
                dependencies[entity_b].add(entity_a)
 
    in_degree = {name: len(deps) for name, deps in dependencies.items()}
 
    # reverse map: dependents[X] = entities that depend on X
    dependents: dict[str, list[str]] = {name: [] for name in entity_names}
    for name, deps in dependencies.items():
        for dep in deps:
            dependents[dep].append(name)
 
    # start with entities that have no dependencies
    queue = [name for name, deg in in_degree.items() if deg == 0]
    sorted_entities: list[str] = []
 
    while queue:
        queue.sort()  # deterministic ordering
        current = queue.pop(0)
        sorted_entities.append(current)
        for dependent in dependents[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
 
    if len(sorted_entities) != len(entity_names):
        raise ValueError(
            "Circular FK dependency detected among entities — "
            "cannot determine a safe INSERT order."
        )
 
    return sorted_entities


def write_schema_sql(spec: SchemaSpec, directory: str):
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    filepath = dir_path / "schema.sql"

    sorted_entity_names = _topological_sort(spec)
    entity_map = spec.entity_map()

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"-- Schema for: {spec.schema_name}\n")

        for entity_name in sorted_entity_names:
            entity = entity_map[entity_name]
            f.write(_build_create_table(entity, spec))
            f.write("\n")
        
        for rel in spec.relationships:
            if should_use_table(rel):
                f.write(_build_relationship_table(rel, spec))
                f.write("\n")

    print(f"  [SQL] Schema written to {filepath.as_posix()}")


def write_data_sql(spec: SchemaSpec, datasets: dict[str, list[dict]], directory: str):
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    filepath = dir_path / "data.sql"

    sorted_entity_names = _topological_sort(spec)
    relationship_names = [
        rel.name for rel in spec.relationships if should_use_table(rel)
    ]
 
    insert_order = sorted_entity_names + relationship_names

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"-- INSERT statements for: {spec.schema_name}\n\n")
        f.write("BEGIN;\n\n")

        for entity_name in insert_order:
            rows = datasets.get(entity_name)
            if not rows:
                continue
            if entity_name in relationship_names:
                table = entity_name.lower()
            else:
                table = _pluralize(entity_name) # Only pluralize names for entity tables
            columns = ", ".join(rows[0].keys())
            f.write(f"-- {entity_name}\n")
            for row in rows:
                values = ", ".join(_sql_value(v) for v in row.values())
                f.write(f"INSERT INTO {table} ({columns}) VALUES ({values});\n")
            f.write("\n")
 
        f.write("COMMIT;\n")

    print(f"  [SQL] Data written to {filepath.as_posix()}")


def write_outputs(spec: SchemaSpec, datasets: dict[str, list[dict]]):
    directory = spec.output.directory
    formats = [fmt.lower() for fmt in spec.output.formats]

    if "sql" in formats:
        print("\nGenerating schema.sql")
        write_schema_sql(spec, directory)
        print("\nGenerating data.sql")
        write_data_sql(spec, datasets, directory)

    for entity_name, rows in datasets.items():
        print(f"\nOutputting '{entity_name}'...")
        if "csv" in formats:
            write_csv(entity_name, rows, directory)


def _build_relationship_table(rel: RelationshipSpec, spec: SchemaSpec) -> str:
    table = rel.name.lower()

    entity_a, entity_b = rel.between
    pk_a = spec.entity_map()[entity_a].primary_key()
    pk_b = spec.entity_map()[entity_b].primary_key()

    lines = []

    # FK Columns
    lines.append(f"    {pk_a.name} {_pg_type(pk_a.type)} NOT NULL")
    lines.append(f"    {pk_b.name} {_pg_type(pk_b.type)} NOT NULL")

    # Relationship Attributes
    for attr in rel.attributes:
        lines.append(f"    {attr.name} {_pg_type(attr.type)} NOT NULL")

    # PK logic
    if rel.type == "many_to_many":
        # M:N → composite key
        lines.append(f"    PRIMARY KEY ({pk_a.name}, {pk_b.name})")

    elif rel.type == "one_to_many":
        # PK should be the MANY side (entity_b)
        lines.append(f"    PRIMARY KEY ({pk_b.name})")

    elif rel.type == "one_to_one":
        lines.append(f"    PRIMARY KEY ({pk_b.name})")
        lines.append(f"    UNIQUE ({pk_a.name})")

    # FOREIGN KEYS
    lines.append(
        f"    FOREIGN KEY ({pk_a.name}) REFERENCES {_pluralize(entity_a)}({pk_a.name})"
    )
    lines.append(
        f"    FOREIGN KEY ({pk_b.name}) REFERENCES {_pluralize(entity_b)}({pk_b.name})"
    )

    body = ",\n".join(lines)

    return (
        f"-- Relationship Table: {table}\n"
        f"CREATE TABLE IF NOT EXISTS {table} (\n{body}\n);\n"
    )
