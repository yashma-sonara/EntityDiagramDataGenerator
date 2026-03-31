from faker import Faker
import numpy as np
import random

from .schema import Distribution, SchemaSpec, EntitySpec, AttributeSpec

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

    return datasets