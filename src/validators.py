from src.schema import SchemaSpec


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
