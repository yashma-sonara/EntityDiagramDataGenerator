from src.schema import SchemaSpec, RelationshipSpec


def semantic_validate(spec: SchemaSpec):
    _check_entity_names(spec)
    _check_primary_keys(spec)
    _check_duplicate_attributes(spec)
    _check_relationships(spec)


def _check_entity_names(spec: SchemaSpec):
    names = [e.name for e in spec.entities]
    if len(names) != len(set(names)):
        duplicates = [n for n in names if names.count(n) > 1]
        raise ValueError(f"Duplicate entity names: {set(duplicates)}")


def _check_primary_keys(spec: SchemaSpec):
    for entity in spec.entities:
        pk_count = sum(1 for a in entity.attributes if a.role == "primary_key")
        if pk_count == 0:
            raise ValueError(
                f"Entity '{entity.name}' has no primary key. "
                f"Add role: 'primary_key' to one attribute."
            )
        if pk_count > 1:
            raise ValueError(
                f"Entity '{entity.name}' has {pk_count} primary keys. "
                f"Only one is allowed."
            )


def _check_duplicate_attributes(spec: SchemaSpec):
    for entity in spec.entities:
        names = [a.name for a in entity.attributes]
        if len(names) != len(set(names)):
            raise ValueError(
                f"Entity '{entity.name}' has duplicate attribute names."
            )


def _check_relationships(spec: SchemaSpec):
    entity_map = spec.entity_map()

    rel_names = [r.name for r in spec.relationships]
    if len(rel_names) != len(set(rel_names)):
        raise ValueError("Duplicate relationship names found.")

    for rel in spec.relationships:
        # entities must exist
        for ent_name in rel.between:
            if ent_name not in entity_map:
                raise ValueError(
                    f"Relationship '{rel.name}' references unknown entity '{ent_name}'."
                )

        # participation keys must match entities
        if set(rel.participation.keys()) != set(rel.between):
            raise ValueError(
                f"Relationship '{rel.name}': participation keys {set(rel.participation.keys())} "
                f"must exactly match connected entities {set(rel.between)}."
            )

        left_name, right_name = rel.between[0], rel.between[1]
        left_rows = entity_map[left_name].rows
        right_rows = entity_map[right_name].rows

        # one-to-one cannot have more rows than min(|A|, |B|)
        if rel.type == "one_to_one":
            max_allowed = min(left_rows, right_rows)
            if rel.rows > max_allowed:
                raise ValueError(
                    f"Relationship '{rel.name}' is one_to_one but requests {rel.rows} rows. "
                    f"Maximum allowed is min({left_rows}, {right_rows}) = {max_allowed}."
                )

        # many-to-many cannot exceed Cartesian product
        if rel.type == "many_to_many":
            max_possible = left_rows * right_rows
            if rel.rows > max_possible:
                raise ValueError(
                    f"Relationship '{rel.name}' requests {rel.rows} rows but only "
                    f"{left_rows} x {right_rows} = {max_possible} unique pairs exist."
                )

        # total participation needs at least |entity| rows overall
        for ent_name, mode in rel.participation.items():
            if mode == "total":
                ent_rows = entity_map[ent_name].rows
                if rel.rows < ent_rows:
                    raise ValueError(
                        f"Relationship '{rel.name}': total participation for '{ent_name}' "
                        f"requires at least {ent_rows} relationship rows, "
                        f"but only {rel.rows} requested."
                    )


def validate_relationships(spec: SchemaSpec, datasets: dict[str, list[dict]]):
    errors = []

    entity_map = spec.entity_map()

    for rel in spec.relationships:
        a, b = rel.between

        pk_a = entity_map[a].primary_key().name
        pk_b = entity_map[b].primary_key().name

        part_a = rel.participation.get(a)
        part_b = rel.participation.get(b)

        if rel.type == "one_to_one":
            errors += validate_one_to_one(rel, datasets, a, b, pk_a, pk_b, part_a, part_b)

        elif rel.type == "one_to_many":
            errors += validate_one_to_many(rel, datasets, a, b, pk_a, pk_b, part_a, part_b)

        elif rel.type == "many_to_many":
            errors += validate_many_to_many(rel, datasets, a, b, pk_a, pk_b, part_a, part_b)

    return errors

def validate_one_to_one(rel: RelationshipSpec, datasets: dict[str, list[dict]], a: str, b: str, pk_a: str, pk_b: str, part_a: str, part_b: str) -> list[str]:
    errors = []

    fk_name = pk_a

    b_rows = datasets[b]

    # FK validity
    valid_a_ids = {row[pk_a] for row in datasets[a]}

    for row in b_rows:
        fk = row.get(fk_name)
        if fk is not None and fk not in valid_a_ids:
            errors.append(f"[{rel.name}] invalid FK in {b}: {fk}")

    # uniqueness (1:1 constraint)
    seen = {}
    for row in b_rows:
        fk = row.get(fk_name)
        if fk is None:
            continue
        if fk in seen:
            errors.append(f"[{rel.name}] violates 1:1, A id {fk} mapped multiple times")
        seen[fk] = True

    # total participation check
    if part_a == "total":
        used = set(row.get(fk_name) for row in b_rows if row.get(fk_name) is not None)
        missing = valid_a_ids - used
        if missing:
            errors.append(f"[{rel.name}] A total participation violated, missing: {missing}")

    return errors

def validate_one_to_many(rel: RelationshipSpec, datasets: dict[str, list[dict]], a: str, b: str, pk_a: str, pk_b: str, part_a: str, part_b: str) -> list[str]:
    errors = []

    fk_name = pk_a

    valid_a = {row[pk_a] for row in datasets[a]}
    b_rows = datasets[b]

    # FK correctness
    for row in b_rows:
        fk = row.get(fk_name)
        if fk is not None and fk not in valid_a:
            errors.append(f"[{rel.name}] invalid FK in {b}: {fk}")

    # B total: every B must have FK
    if part_b == "total":
        for row in b_rows:
            if row.get(fk_name) is None:
                errors.append(f"[{rel.name}] B total violated: null FK in {b}")

    # A total: every A must appear at least once in B
    if part_a == "total":
        used_a = {row[fk_name] for row in b_rows if row.get(fk_name) is not None}
        missing = valid_a - used_a
        if missing:
            errors.append(f"[{rel.name}] A total violated, missing: {missing}")

    return errors

def validate_many_to_many(rel: RelationshipSpec, datasets: dict[str, list[dict]], a: str, b: str, pk_a: str, pk_b: str, part_a: str, part_b: str) -> list[str]:
    errors = []

    table = datasets.get(rel.name, [])
    if not table:
        errors.append(f"[{rel.name}] missing relationship table")
        return errors

    valid_a = {row[pk_a] for row in datasets[a]}
    valid_b = {row[pk_b] for row in datasets[b]}

    seen = set()

    a_seen = set()
    b_seen = set()

    for row in table:
        a_id = row.get(pk_a)
        b_id = row.get(pk_b)

        # FK checks
        if a_id not in valid_a:
            errors.append(f"[{rel.name}] invalid A FK: {a_id}")
        if b_id not in valid_b:
            errors.append(f"[{rel.name}] invalid B FK: {b_id}")

        # duplicate check
        if (a_id, b_id) in seen:
            errors.append(f"[{rel.name}] duplicate pair {(a_id, b_id)}")
        seen.add((a_id, b_id))

        a_seen.add(a_id)
        b_seen.add(b_id)

    # participation
    if part_a == "total":
        missing_a = valid_a - a_seen
        if missing_a:
            errors.append(f"[{rel.name}] A total violated: {missing_a}")

    if part_b == "total":
        missing_b = valid_b - b_seen
        if missing_b:
            errors.append(f"[{rel.name}] B total violated: {missing_b}")

    return errors