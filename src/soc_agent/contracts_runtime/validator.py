from __future__ import annotations

from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from .loader import load_all_schemas


class SchemaValidationError(ValueError):
    pass


class SchemaValidator:
    def __init__(self, schemas: dict[str, dict[str, Any]] | None = None, repo_root: Path | None = None):
        self._schemas = schemas or load_all_schemas(repo_root)
        self._validators: dict[str, Draft202012Validator] = {}
        self._build_validators()

    def _build_validators(self) -> None:
        # Register schemas by both filename-like URI and $id for local $ref resolution
        registry: dict[str, Any] = {}
        for name, schema in self._schemas.items():
            registry[name] = schema
            sid = schema.get("$id")
            if isinstance(sid, str):
                registry[sid] = schema
            # allow refs like "common.schema.json#/$defs/..."
            registry[f"https://soc-agent.local/contracts/{name}"] = schema
        for name, schema in self._schemas.items():
            resolver = None
            try:
                from referencing import Registry, Resource
                from referencing.jsonschema import DRAFT202012

                reg = Registry().with_resources(
                    [(uri, Resource.from_contents(contents, default_specification=DRAFT202012)) for uri, contents in registry.items()]
                )
                self._validators[name] = Draft202012Validator(schema, registry=reg, format_checker=FormatChecker())
            except Exception:
                # fallback without explicit registry; refs may still resolve in simple cases
                self._validators[name] = Draft202012Validator(schema, format_checker=FormatChecker())

    def validate(self, schema_name: str, instance: Any) -> None:
        validator = self._validators.get(schema_name)
        if validator is None:
            available = ", ".join(sorted(self._validators.keys())[:10])
            raise SchemaValidationError(f"Unknown schema: {schema_name}. Available (sample): {available}")
        errors = sorted(validator.iter_errors(instance), key=lambda e: e.path)
        if errors:
            msgs = []
            for e in errors[:10]:
                loc = "$" + "".join([f"[{p}]" if isinstance(p, int) else f".{p}" for p in e.path])
                msgs.append(f"{loc}: {e.message}")
            raise SchemaValidationError(f"Schema validation failed for {schema_name}: " + "; ".join(msgs))

    def is_valid(self, schema_name: str, instance: Any) -> bool:
        try:
            self.validate(schema_name, instance)
            return True
        except Exception:
            return False

    @property
    def schema_names(self) -> list[str]:
        return sorted(self._schemas.keys())
