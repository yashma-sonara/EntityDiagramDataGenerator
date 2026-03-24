import sys
from parser import parse_schema


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <schema_file.json>")
        sys.exit(1)

    schema_path = sys.argv[1]

    try:
        spec = parse_schema(schema_path)
        print(f"Schema '{spec.schema_name}' parsed and validated successfully.")
        print(f"  Entities   : {[e.name for e in spec.entities]}")
        print(f"  Relationships: {[r.name for r in spec.relationships]}")
        print(f"  Output dir : {spec.output.directory}")
        print(f"  Formats    : {spec.output.formats}")
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
