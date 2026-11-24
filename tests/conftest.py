from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from soc_agent.contracts_runtime.loader import find_repo_root, get_contracts_dir, load_all_schemas


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return find_repo_root(Path(__file__).resolve().parent)


@pytest.fixture(scope="session")
def contracts_dir(repo_root: Path) -> Path:
    return get_contracts_dir(repo_root)


@pytest.fixture(scope="session")
def all_schemas(repo_root: Path) -> dict:
    return load_all_schemas(repo_root)


@pytest.fixture
def fixed_now() -> str:
    return datetime(2026, 11, 23, 12, 0, 0, tzinfo=timezone.utc).isoformat()


@pytest.fixture
def make_id():
    def _make(prefix: str = "id") -> str:
        return f"{prefix}-{uuid4()}"

    return _make
