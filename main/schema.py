JSON_SCHEMA = {
    "type": "object",
    "required": ["schema_name", "output", "entities", "relationships"],
    "properties": {
        "schema_name": {"type": "string"},
        "output": {
            "type": "object",
            "required": ["formats", "directory"],
            "properties": {
                "formats": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["csv", "sql"]},
                    "minItems": 1
                },
                "directory": {"type": "string"}
            }
        },
        "entities": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "rows", "attributes"],
                "properties": {
                    "name": {"type": "string"},
                    "rows": {"type": "integer", "minimum": 1},
                    "attributes": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["name", "type"],
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "role": {"type": "string", "enum": ["primary_key"]},
                                "unique": {"type": "boolean"},
                                "generator": {"type": "string"},
                                "distribution": {
                                    "type": "object",
                                    "required": ["kind"],
                                    "properties": {
                                        "kind": {
                                            "type": "string",
                                            "enum": ["uniform", "choice", "normal", "poisson"]
                                        }
                                    },
                                    "additionalProperties": True
                                }
                            }
                        }
                    }
                }
            }
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "type", "between", "rows", "participation"],
                "properties": {
                    "name": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["one_to_one", "one_to_many", "many_to_many"]
                    },
                    "between": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 2,
                        "maxItems": 2
                    },
                    "rows": {"type": "integer", "minimum": 0},
                    "participation": {
                        "type": "object",
                        "additionalProperties": {
                            "type": "string",
                            "enum": ["total", "partial"]
                        }
                    },
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["name", "type"],
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    }
}
