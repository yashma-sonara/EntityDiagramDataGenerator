from faker import Faker
from typing import List, Tuple, Any
import numpy as np
import random

from .schema import Distribution, SchemaSpec, EntitySpec, AttributeSpec, RelationshipSpec

CUSTOM_GENERATORS: dict = {
    # --- Academic ---
    "course_title": lambda f: random.choice([
        "Algorithms & Complexity", "Data Structures", "Operating Systems", "Computer Networks",
        "Database Systems", "Software Engineering", "Computer Architecture", "Programming Languages",
        "Artificial Intelligence", "Machine Learning", "Deep Learning", "Data Mining",
        "Natural Language Processing", "Computer Vision", "Reinforcement Learning",
        "Discrete Mathematics", "Linear Algebra", "Probability & Statistics", "Calculus",
        "Distributed Systems", "Cloud Computing", "Cybersecurity", "Embedded Systems",
        "Human-Computer Interaction", "Computer Graphics", "Compiler Design",
    ]),
    "course_code": lambda f: f.bothify("??###").upper(),
    "student_id": lambda f: f"S{np.random.randint(1000000, 9999999)}",
    "grade": lambda f: random.choices(
        ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F"],
        weights=[5, 10, 10, 15, 20, 15, 10, 8, 5, 2]
    )[0],
    "semester": lambda f: f"{random.choice(['AY23/24', 'AY24/25', 'AY25/26'])} {random.choice(['S1', 'S2'])}",
    "degree": lambda f: random.choice([
        "Bachelor of Computing (Computer Science)",
        "Bachelor of Computing (Information Systems)",
        "Bachelor of Science (Data Science & Analytics)",
        "Bachelor of Software Engineering",
        "Bachelor of Information Security",
        "Bachelor of Arts (Digital Communication)",
        "Bachelor of Business Administration",
        "Bachelor of Engineering (Electrical)",
    ]),
    
    # --- Employee ---
    "employee_id": lambda f: f"E{np.random.randint(1000000, 9999999)}",
    "department": lambda f: random.choice(["Engineering", "Marketing", "Finance", "HR", "Sales", "Operations", "Legal"]),
    "employment_type": lambda f: random.choice(["Full-Time", "Part-Time", "Contract", "Intern"]),

    # --- Orders ---
    "order_id": lambda f: f"ORD-{np.random.randint(100000, 999999)}",
    "order_status": lambda f: random.choice(["Pending", "Processing", "Shipped", "Delivered", "Cancelled", "Refunded"]),
    "product_category": lambda f: random.choice(["Electronics", "Clothing", "Books", "Home & Living", "Sports", "Beauty", "Toys"]),
    "payment_method": lambda f: random.choice(["Credit Card", "Debit Card", "PayPal", "Bank Transfer", "Crypto"]),
    "shipping_method": lambda f: random.choice(["Standard", "Express", "Next-Day", "Self-Collect"]),

    # --- Healthcare ---
    "patient_id": lambda f: f"P{np.random.randint(100000, 999999)}",
    "blood_type": lambda f: random.choice(["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]),
    "ward": lambda f: random.choice(["A1", "A2", "B1", "B2", "C1", "ICU", "Emergency"]),
    "diagnosis": lambda f: random.choice(["Hypertension", "Diabetes", "Asthma", "Fracture", "Migraine", "Flu"]),

    # --- General ---
    "status": lambda f: random.choice(["Active", "Inactive", "Pending", "Suspended"]),
    "priority": lambda f: random.choice(["Low", "Medium", "High", "Critical"]),
    "rating": lambda f: round(np.random.uniform(1.0, 5.0), 1),
    "percentage": lambda f: round(np.random.uniform(0.0, 100.0), 2),
}


def sample_numeric(dist: Distribution) -> float:
    kind   = dist.kind
    params = dist.params

    if kind == "uniform":
        return np.random.uniform(params["min"], params["max"])
    if kind == "normal":
        return np.random.normal(params["mean"], params["std"])
    if kind == "poisson":
        return np.random.poisson(params["lam"])

    raise ValueError(f"Unknown numeric distribution: '{kind}'")


def sample_choice(dist: Distribution):
    values  = dist.params.get("values")
    weights = dist.params.get("weights")

    if values is None:
        raise ValueError("'choice' distribution requires a 'values' list in params.")

    if weights is not None:
        weights = np.array(weights, dtype=float)
        weights /= weights.sum() # normalisation to allow usage of relative weights
        return np.random.choice(values, p=weights).item()

    return np.random.choice(values).item()


def generate_value(attr: AttributeSpec, fake: Faker):
    if attr.generator is not None:
        gen = CUSTOM_GENERATORS.get(attr.generator)
        if gen is None:
            raise ValueError(f"Unknown generator: '{attr.generator}'")
        return gen(fake)

    if attr.distribution is not None:
        kind = attr.distribution.kind

        if kind == "choice":
            return sample_choice(attr.distribution)

        if attr.type == "int":
            return int(sample_numeric(attr.distribution))
        if attr.type == "float":
            return float(sample_numeric(attr.distribution))

    if hasattr(fake, attr.type):
        return getattr(fake, attr.type)()

    if attr.type == "int":
        return int(np.random.randint(0, 1_000_000))
    if attr.type == "float":
        return float(np.random.random())
    if attr.type == "boolean":
        return bool(np.random.choice([True, False]))
    if attr.type == "string":
        return fake.word()

    raise ValueError(f"Unsupported attribute type: '{attr.type}'")


def generate_unique(generator, used_values: set, max_attempts: int = 10_000):
    for _ in range(max_attempts):
        value = generator()
        if value not in used_values:
            used_values.add(value)
            return value
    raise ValueError(
        f"Could not generate a unique value after {max_attempts} attempts. "
        "Consider increasing the entity row count or widening the distribution range."
    )


def generate_entity(entity: EntitySpec, fake: Faker) -> list[dict]:
    unique_sets: dict[str, set] = {}
    rows: list[dict] = []

    for row_index in range(entity.rows):
        row: dict = {}

        for attr in entity.attributes:
            is_pk     = attr.role == "primary_key"
            is_unique = attr.unique or is_pk

            if is_pk and attr.type == "int" and attr.distribution is None and attr.generator is None:
                row[attr.name] = row_index + 1
                unique_sets.setdefault(attr.name, set()).add(row_index + 1)
                continue

            def generate(a=attr):
                return generate_value(a, fake)

            if is_unique:
                unique_sets.setdefault(attr.name, set())
                row[attr.name] = generate_unique(generate, unique_sets[attr.name])
            else:
                row[attr.name] = generate()

        rows.append(row)

    return rows


def generate_dataset(spec: SchemaSpec) -> dict[str, list[dict]]:
    fake = Faker()
    datasets: dict[str, list[dict]] = {}

    for entity in spec.entities:
        datasets[entity.name] = generate_entity(entity, fake)
    
    relationship_data = generate_relationship(spec, datasets)

    datasets.update(relationship_data)

    return datasets


def generate_rel_attrs(rel: RelationshipSpec) -> dict:
    # Uses the same logic as generate_value for attributes on the relationship itself
    fake = Faker()
    return {attr.name: generate_value(attr, fake) for attr in rel.attributes}


def should_use_table(rel: RelationshipSpec) -> bool: 
    return rel.type == "many_to_many" or len(rel.attributes) > 0


def gen_one_to_one_pairs(ids_a: List[Any], ids_b: List[Any], part_a: str, part_b: str) -> List[Tuple[Any, Any]]:
    A = list(ids_a)
    B = list(ids_b)

    random.shuffle(A)
    random.shuffle(B)

    pairs = []

    # Case 1: total-total
    # Every A must map to one B AND every B must map to one A
    if part_a == "total" and part_b == "total":
        if len(A) != len(B):
            raise ValueError("1:1 total-total requires equal sizes")
        pairs = list(zip(A, B))

    # Case 2: A total, B partial
    # Every A must map to some B, but some B can be unmapped
    elif part_a == "total":
        if len(B) < len(A):
            raise ValueError("Not enough B for A total")
        pairs = [(A[i], B[i]) for i in range(len(A))]

    # Case 3: B total, A partial
    # Every B must map to some A, but some A can be unmapped
    elif part_b == "total":
        if len(A) < len(B):
            raise ValueError("Not enough A for B total")
        pairs = [(A[i], B[i]) for i in range(len(B))]

    # Case 4: partial-partial
    # random subset of unique pairs
    else:
        k = random.randint(0, min(len(A), len(B)))
        pairs = list(zip(random.sample(A, k), random.sample(B, k)))

    return pairs


def gen_one_to_many_pairs(ids_a: List[Any], ids_b: List[Any], part_a: str, part_b: str) -> List[Tuple[Any, Any]]:
    # A = one side, B = many side
    pairs = []
    used_b = set()
    B = list(ids_b)

    # Case 1: B total
    # Every B must map to exactly one A
    if part_b == "total":
        for b in ids_b:
            a = random.choice(ids_a)
            pairs.append((a, b))
            used_b.add(b)

    # Case 2: A total
    # Every A must appear at least once
    if part_a == "total":
        used_a = {a for a, _ in pairs}
        for a in ids_a:
            if a not in used_a:
                # Find a B that has not been assigned yet to maintain 1:N integrity
                available_b = [b for b in B if b not in used_b]

                if not available_b:
                    raise ValueError("Not enough B to satisfy A total")
                
                b = random.choice(available_b)
                pairs.append((a, b))
                used_b.add(b)

    # Fill the rest of the relationships randomly based on B's capacity
    remaining_b = [b for b in B if b not in used_b]
    extra = random.randint(0, len(ids_b))
    for _ in range(extra):
        if not remaining_b:
            break
        
        a = random.choice(ids_a)
        b = random.choice(remaining_b)
        remaining_b.remove(b)
        pairs.append((a, b))

    return pairs


def gen_many_to_many_pairs(ids_a: List[Any], ids_b: List[Any], part_a: str, part_b: str, target_rows: int) -> List[Tuple[Any, Any]]: 
    pairs = []
    used_pairs = set()

    # CASE 1: A total
    # Every A must appear at least once
    if part_a == "total":
        for a in ids_a:
            b = random.choice(ids_b)
            pair = (a, b)
            if pair not in used_pairs:
                used_pairs.add(pair)
                pairs.append(pair)

    # CASE 2: B total 
    # Every B must appear at least once
    if part_b == "total":
        used_b = {b for _, b in pairs}
        for b in ids_b:
            if b not in used_b:
                a = random.choice(ids_a)
                pair = (a, b)
                if pair not in used_pairs:
                    used_pairs.add(pair)
                    pairs.append(pair)

    # Fill until we reach the user specified row count
    while len(pairs) < target_rows:
        a = random.choice(ids_a)
        b = random.choice(ids_b)
        pair = (a, b)

        if pair not in used_pairs:
            used_pairs.add(pair)
            pairs.append(pair)

    return pairs


def assign_fk(pairs: List[Tuple[Any, Any]], entity_a: str, entity_b: str, pk_a: str, pk_b: str, datasets: dict[str, list[dict]]):
    fk_name = entity_a.lower() + '_' + pk_a

    # Initialize all rows with None (to handle partial participation)
    for row in datasets[entity_b]:
        row[fk_name] = None

    # Assign FK values based on generated pairs
    for a, b in pairs:
        for row in datasets[entity_b]:
            if row[pk_b] == b: # find matching B row
                row[fk_name] = a
                break


def build_relationship_table(pairs: List[Tuple[Any, Any]], pk_a: str, pk_b: str, rel: RelationshipSpec) -> dict[str, list[dict]]:
    rows = []
    for a, b in pairs:
        rows.append({
            pk_a: a,
            pk_b: b,
            **generate_rel_attrs(rel)
        })
    return rows


def generate_relationship(spec: SchemaSpec, datasets: dict[str, list[dict]]) -> dict[str, list[dict]]:
    relationship_data = {}

    for rel in spec.relationships:
        entity_a, entity_b = rel.between

        pk_a = spec.entity_map()[entity_a].primary_key().name
        pk_b = spec.entity_map()[entity_b].primary_key().name

        ids_a = [row[pk_a] for row in datasets[entity_a]]
        ids_b = [row[pk_b] for row in datasets[entity_b]]

        part_a = rel.participation.get(entity_a)
        part_b = rel.participation.get(entity_b)
        
        if rel.type == "one_to_one":
            pairs = gen_one_to_one_pairs(ids_a, ids_b, part_a, part_b)

        elif rel.type == "one_to_many":
            pairs = gen_one_to_many_pairs(ids_a, ids_b, part_a, part_b)

        elif rel.type == "many_to_many":
            target_rows = rel.rows
            pairs = gen_many_to_many_pairs(ids_a, ids_b, part_a, part_b, target_rows)

        # Only create table for relationship set that has attributes
        # and cardinality constraints of many_to_many
        if should_use_table(rel):
            relationship_data[rel.name] = build_relationship_table(pairs, pk_a, pk_b, rel)

        # Update the datasets for the foreign key column
        else:
            if rel.type == "one_to_one":
                assign_fk(pairs, entity_a, entity_b, pk_a, pk_b, datasets)

            elif rel.type == "one_to_many":
                assign_fk(pairs, entity_a, entity_b, pk_a, pk_b, datasets)

    return relationship_data

