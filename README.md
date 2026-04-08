# EntityDiagramDataGenerator

EntityDiagramDataGenerator generates sample data from a JSON schema and writes CSV and SQL outputs for loading a database.

## How To Run:

1. Install Dependencies:</br>
   `python -m pip install -r requirements.txt`

2. Run the generator with your schema: </br>
   `python main.py examples/sample_schema.json`

Example console output:

```text
Schema 'university' parsed and validated successfully.
  Entities   : ['Student', 'Course']
  Relationships: ['Enrolls']
  Output dir : out/university
  Formats    : ['csv', 'sql']

Generating entity data...
  Student: 100 rows generated
  Course: 80 rows generated

Writing outputs to 'out/university'...

Generating schema.sql
  [SQL] Schema written to out/university/schema.sql

Generating data.sql
  [SQL] Data written to out/university/data.sql

Outputting 'Student'...
  [CSV] Written 100 rows to out/university/Student.csv

Outputting 'Course'...
  [CSV] Written 80 rows to out/university/Course.csv

Data generation completed.

All relationships valid.
```

Part 1 Details done below : Yashma

- main.py calls parse_schema
- parse_schema reads JSON file -> checks against JSON_SCHEMA -> converts into SchemaSpec, EntitySpec, AttributeSpec, RelationshipSpec, OutputSpec python objects
- schema.py is the main in-memory data model for the python objects
- main.py prints out parsed

Part 2 Details done below : Xuan Xuan

- main.py calls generate_dataset to generate a dict of data values, then calls write_outputs to output the data in csv and sql formats depending on user specification.

`src/data_generator.py` handles the data generation logic

- Supports custom semantic generators like `course_code`, `grade`, `student_id`, and others. See the Supported Custom Generators section for the full list.
- Supports attribute-level distributions that can be specified in the input schema under `attribute > distribution` :
  - `uniform`
  - `normal`
  - `poisson`
  - `choice`
- Supports Faker-backed attribute types via the Python `faker` library. If an attribute `type` matches a Faker provider name, the generator will call that provider. See the full provider reference here: [Python Faker Provider Documentation](https://faker.readthedocs.io/en/master/providers.html)
- If an integer primary key has no `generator` or `distribution`, sequential integers are generated automatically.
- Unique attributes are enforced by retrying value generation until a new value is found. `generate_unique()` retries up to 10,000 times before raising an error.
- For each entity, rows are created one at a time. `generate_value()` generates the value with this priority:
  1. use a declared `generator`
  2. use `distribution` via `sample_numeric()` (uniform/normal/poisson) or `sample_choice()` (choice)
  3. use a matching Faker provider if available
  4. otherwise, fall back to default random values for `int`, `float`, `boolean`, or `string`
     </br></br>

`src/output.py` handles the SQL and CSV output logic

- Writes one CSV file per entity when `csv` output is requested.
- Writes `schema.sql` and `data.sql` when `sql` output is requested.
- SQL output maps DSL types to PostgreSQL types and pluralizes entity names for table names using `inflect`.

Part 3 Details done below : Qing Yee

`src/relationship_generator.py` handles relationship generation logic:

- Supports `binary` relationships only.
- Generates relationship pairs based on cardinality:
  - `one_to_one`
  - `one_to_many`
  - `many_to_many`
- Enforces participation constraints:
  - `total` → ensures all entities on that side appear in at least one relationship.
  - `partial` → allows optional participation.
- Join selectivity is handled by the `rows` parameter in the input schema.

- Foreign Key (FK) embedding:
  - Used for one_to_one and one_to_many relationships without attributes.
  - Adds FK fields to the right-hand entity in `between` parameter for the RelationshipSpec.
  - Initializes FK fields to `NULL`, then assigns values based on generated pairs.

- Relationship tables:
  - Used for many_to_many relationships or when the relationship includes attributes.
  - Creates a separate table with:
    - Foreign keys referencing both entities.
    - Additional relationship attributes.
    - Appropriate primary key:
      - `1:N` → PK is the many-side FK.
      - `1:1` → PK is single FK, with `UNIQUE` constraint on the other.
      - `N:M` → composite primary key.

`src/validators.py` to check for cardinality and participation constraints.

## Supported Custom Generators

This project includes custom generators for common semantic attributes.

In your input schema, use `generator: "<generator_name>"` to apply one of these custom generators.

- Academic
  - `course_title`
  - `course_code`
  - `student_id`
  - `grade`
  - `semester`
  - `degree`

- Employee
  - `employee_id`
  - `department`
  - `employment_type`

- Orders
  - `order_id`
  - `order_status`
  - `product_category`
  - `payment_method`
  - `shipping_method`

- Healthcare
  - `patient_id`
  - `blood_type`
  - `ward`
  - `diagnosis`

- General
  - `status`
  - `priority`
  - `rating`
  - `percentage`
