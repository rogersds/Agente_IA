from __future__ import annotations

import os
import stat

import pytest

from soc_agent.adapters.policy_engine.opa_adapter import find_opa_binary


def _make_executable(path):
    path.write_text("#!/bin/sh\n", encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _opa_name_for_path():
    return "opa.exe" if os.name == "nt" else "opa"


def test_find_opa_uses_valid_opa_bin(tmp_path, monkeypatch):
    fake = _make_executable(tmp_path / "opa.exe")
    monkeypatch.setenv("OPA_BIN", str(fake))
    monkeypatch.setenv("PATH", "")
    assert find_opa_binary() == str(fake)


def test_find_opa_invalid_opa_bin_falls_back_to_path(tmp_path, monkeypatch):
    invalid = tmp_path / "missing-opa.exe"
    fake_on_path = _make_executable(tmp_path / _opa_name_for_path())
    monkeypatch.setenv("OPA_BIN", str(invalid))
    monkeypatch.setenv("PATH", str(tmp_path))
    assert os.path.normcase(find_opa_binary()) == os.path.normcase(str(fake_on_path))


def test_find_opa_only_path(tmp_path, monkeypatch):
    fake_on_path = _make_executable(tmp_path / _opa_name_for_path())
    monkeypatch.delenv("OPA_BIN", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert os.path.normcase(find_opa_binary()) == os.path.normcase(str(fake_on_path))


def test_find_opa_none_without_require_opa(monkeypatch):
    monkeypatch.delenv("OPA_BIN", raising=False)
    monkeypatch.setenv("PATH", "")
    monkeypatch.delenv("REQUIRE_OPA", raising=False)
    assert find_opa_binary() is None


def test_find_opa_none_with_require_opa(monkeypatch):
    monkeypatch.delenv("OPA_BIN", raising=False)
    monkeypatch.setenv("PATH", "")
    monkeypatch.setenv("REQUIRE_OPA", "1")
    # descoberta retorna None; enforcement de REQUIRE_OPA é do caller/helper de teste
    assert find_opa_binary() is None
