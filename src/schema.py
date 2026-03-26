from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Distribution:
    kind: str
    params: Dict[str, Any]


@dataclass
class AttributeSpec:
    name: str
    type: str
    role: Optional[str] = None
    unique: bool = False
    generator: Optional[str] = None
    distribution: Optional[Distribution] = None


@dataclass
class EntitySpec:
    name: str
    rows: int
    attributes: List[AttributeSpec]

    def primary_key(self) -> "AttributeSpec":
        for attr in self.attributes:
            if attr.role == "primary_key":
                return attr
        raise ValueError(f"No primary key found in entity '{self.name}'")


@dataclass
class RelationshipSpec:
    name: str
    type: str
    between: List[str]
    rows: int
    participation: Dict[str, str]
    attributes: List[AttributeSpec] = field(default_factory=list)


@dataclass
class OutputSpec:
    formats: List[str]
    directory: str


@dataclass
class SchemaSpec:
    schema_name: str
    output: OutputSpec
    entities: List[EntitySpec]
    relationships: List[RelationshipSpec]

    def entity_map(self) -> Dict[str, EntitySpec]:
        return {e.name: e for e in self.entities}
