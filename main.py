import sys
from src.parser import parse_schema
from src.data_generator import generate_dataset
from src.output import write_outputs
from src.validators import validate_relationships

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

        print("\nGenerating entity data...")
        datasets = generate_dataset(spec)
        for name, rows in datasets.items():
            print(f"  {name}: {len(rows)} rows generated")

        print(f"\nWriting outputs to '{spec.output.directory}'...")
        write_outputs(spec, datasets)
    
        print("\nData generation completed.")

        errors = validate_relationships(spec, datasets)

        if errors:
            print("\nRelationship validation failed:")
            for e in errors:
                print("-", e)
        else:
            print("\nAll relationships valid.")
        
    except (ValueError, FileNotFoundError) as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
