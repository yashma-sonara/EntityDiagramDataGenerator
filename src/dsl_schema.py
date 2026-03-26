JSON_SCHEMA = {
    "type": "object",
    "required": ["schema_name", "output", "entities", "relationships"],
    "additionalProperties": False,
    "properties": {
        "schema_name": {"type": "string", "minLength": 1},

        "output": {
            "type": "object",
            "required": ["formats", "directory"],
            "additionalProperties": False,
            "properties": {
                "formats": {
                    "type": "array",
                    "minItems": 1,
                    "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "enum": ["csv", "sql"]
                    }
                },
                "directory": {"type": "string", "minLength": 1}
            }
        },

        "entities": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "rows", "attributes"],
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "rows": {"type": "integer", "minimum": 1},
                    "attributes": {
                        "type": "array",
                        "minItems": 1,
                        "items": {
                            "type": "object",
                            "required": ["name", "type"],
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "type": {
                                    "type": "string",
                                    "enum": [
                                        "int", "string", "float",
                                        "name", "email", "city",
                                        "country", "phone", "date",
                                        "boolean", "text"
                                    ]
                                },
                                "role": {
                                    "type": "string",
                                    "enum": ["primary_key"]
                                },
                                "unique": {"type": "boolean"},
                                "generator": {
                                    "type": "string"
                                },
                                "distribution": {
                                    "type": "object",
                                    "required": ["kind"],
                                    "additionalProperties": True,
                                    "properties": {
                                        "kind": {
                                            "type": "string",
                                            "enum": ["uniform", "choice", "normal", "poisson"]
                                        }
                                    }
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
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "type": {
                        "type": "string",
                        "enum": ["one_to_one", "one_to_many", "many_to_many"]
                    },
                    "between": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": {"type": "string"}
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
                            "additionalProperties": False,
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "generator": {"type": "string"},
                                "distribution": {
                                    "type": "object",
                                    "required": ["kind"],
                                    "additionalProperties": True,
                                    "properties": {
                                        "kind": {
                                            "type": "string",
                                            "enum": ["uniform", "choice", "normal", "poisson"]
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
