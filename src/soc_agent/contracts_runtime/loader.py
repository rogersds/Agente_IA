from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_FEATURE_CONTRACTS_REL = Path("specs/001-soc-triage-correlacao/contracts")


def find_repo_root(start: Path | None = None) -> Path:
    cur = (start or Path.cwd()).resolve()
    for p in [cur, *cur.parents]:
        if (p / ".specify").is_dir() and (p / "specs").is_dir():
            return p
        if (p / ".git").exists():
            return p
    return cur


def get_contracts_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    path = root / DEFAULT_FEATURE_CONTRACTS_REL
    if not path.is_dir():
        raise FileNotFoundError(f"Contracts directory not found: {path}")
    return path


def get_schemas_dir(repo_root: Path | None = None) -> Path:
    return get_contracts_dir(repo_root) / "schemas"


def get_policy_dir(repo_root: Path | None = None) -> Path:
    return get_contracts_dir(repo_root) / "policy"


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_schema(name: str, repo_root: Path | None = None) -> dict[str, Any]:
    """Load a schema by filename (e.g. 'triage-result.schema.json')."""
    schema_path = get_schemas_dir(repo_root) / name
    if not schema_path.is_file():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    return load_json(schema_path)


def load_all_schemas(repo_root: Path | None = None) -> dict[str, dict[str, Any]]:
    schemas_dir = get_schemas_dir(repo_root)
    out: dict[str, dict[str, Any]] = {}
    for p in sorted(schemas_dir.glob("*.schema.json")):
        out[p.name] = load_json(p)
    return out


def load_policy_text(name: str = "action_proposal.rego", repo_root: Path | None = None) -> str:
    path = get_policy_dir(repo_root) / name
    if not path.is_file():
        raise FileNotFoundError(f"Policy file not found: {path}")
    return path.read_text(encoding="utf-8")
