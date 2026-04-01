import csv
import inflect
from typing import cast, Any
from pathlib import Path
from .schema import SchemaSpec, EntitySpec

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


def _build_create_table(entity: EntitySpec) -> str:
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

    # TODO: Add Foreign Key constraints based on relationships

    body = ",\n".join(lines)
    return (
        f"-- Table: {table}\n"
        f"CREATE TABLE IF NOT EXISTS {table} (\n"
        f"{body}\n"
        f");\n"
    )


def write_schema_sql(spec: SchemaSpec, directory: str):
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    filepath = dir_path / "schema.sql"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"-- Schema for: {spec.schema_name}\n")

        for entity in spec.entities:
            f.write(_build_create_table(entity))
            f.write("\n")

    print(f"  [SQL] Schema written to {filepath.as_posix()}")


def write_data_sql(spec: SchemaSpec, datasets: dict[str, list[dict]], directory: str):
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    filepath = dir_path / "data.sql"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"-- INSERT statements for: {spec.schema_name}\n\n")

        for entity_name, rows in datasets.items():
            if not rows:
                continue
            table = _pluralize(entity_name)
            columns = ", ".join(rows[0].keys())
            f.write(f"-- {entity_name}\n")
            for row in rows:
                values = ", ".join(_sql_value(v) for v in row.values())
                f.write(f"INSERT INTO {table} ({columns}) VALUES ({values});\n")
            f.write("\n")

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