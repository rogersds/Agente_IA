from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Caminhos/artefatos locais que não devem ser versionados
FORBIDDEN_PATH_PREFIXES = (
    "runtime/",
    "logs/",
    "data/local/",
    "secrets/",
)
FORBIDDEN_PATH_EXACT_NAMES = {
    ".env",
}
FORBIDDEN_GLOBS_SUFFIXES = (
    ".db",
    ".sqlite",
    ".sqlite3",
)

# Heurísticas simples para segredos óbvios em arquivos rastreados (evitar falsos positivos em docs de exemplo)
SECRET_PATTERNS = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"ghp_[A-Za-z0-9]{20,}"), "GitHub token"),
    (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"-----BEGIN (?:RSA|EC|OPENSSH|DSA)? ?PRIVATE KEY-----"), "Private key material"),
    (re.compile(r"AIza[0-9A-Za-z\-_]{20,}"), "Google API key"),
]


def git_tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], cwd=REPO, text=True)
    return [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]


def is_forbidden_path(path: str) -> str | None:
    p = path.replace("\\", "/")
    for pref in FORBIDDEN_PATH_PREFIXES:
        if p == pref.rstrip("/") or p.startswith(pref):
            return f"caminho local/artefato proibido versionado: {p}"
    name = Path(p).name
    if name in FORBIDDEN_PATH_EXACT_NAMES or name.startswith(".env."):
        return f"arquivo de ambiente potencialmente sensível versionado: {p}"
    for suf in FORBIDDEN_GLOBS_SUFFIXES:
        if p.endswith(suf):
            return f"artefato local/banco versionado: {p}"
    return None


def scan_for_secrets(path: str) -> list[str]:
    # Ignora binários prováveis por extensão comum
    p = REPO / path
    if not p.exists() or p.is_dir():
        return []
    try:
        data = p.read_bytes()
    except Exception:
        return []
    if b"\x00" in data[:4096]:
        return []
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        return []
    findings = []
    for rx, label in SECRET_PATTERNS:
        if rx.search(text):
            findings.append(f"possível segredo ({label}) em arquivo rastreado: {path}")
    return findings


def main() -> int:
    try:
        files = git_tracked_files()
    except Exception as e:
        print(f"HIGIENE: falha ao listar arquivos rastreados: {e}", file=sys.stderr)
        return 2

    errors: list[str] = []
    for f in files:
        reason = is_forbidden_path(f)
        if reason:
            errors.append(reason)
        errors.extend(scan_for_secrets(f))

    if errors:
        print("HIGIENE: falha - problemas encontrados:", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        return 1

    print(f"HIGIENE: ok ({len(files)} arquivos rastreados verificados)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
