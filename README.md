# EntityDiagramDataGenerator
How To Run: 

`python -m pip install -r requirements.txt`

Test:
`python main.py examples/sample_schema.json`

Output is like: 
`Schema 'university' parsed and validated successfully.
  Entities   : ['Student', 'Course']
  Relationships: ['Enrolls']
  Output dir : out/university
  Formats    : ['csv', 'sql']`

Part 1 Details done below : Yashma 
- main.py calls parse_schema
- parse_schema reads JSON file -> checks against JSON_SCHEMA -> converts into SchemaSpec, EntitySpec, AttributeSpec, RelationshipSpec, OutputSpec python objects
- schemy.py is the main in-memory data model for the python objects
- main.py prints out parsed 

To be done: