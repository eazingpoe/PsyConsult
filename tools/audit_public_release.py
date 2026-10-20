#!/usr/bin/env python3
"""Privacy-conscious pre-publication audit for PsyConsult.

Prints paths, rule names and line numbers only; never prints matched secret values.
This is a heuristic checklist, not a comprehensive security or legal audit.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()
SKIP_DIRS = {
    ".git", "node_modules", "dist", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "coverage",
}
TEXT_SUFFIXES = {
    ".py", ".js", ".ts", ".vue", ".json", ".yaml", ".yml", ".md",
    ".txt", ".toml", ".ini", ".cfg", ".sh", ".ps1", ".csv", ".env",
}
MAX_TEXT_BYTES = 2 * 1024 * 1024

SECRET_PATTERNS = [
    ("private-key-header", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("generic-api-key-assignment", re.compile(
        r"""(?i)\b(?:OPENAI_API_KEY|DASHSCOPE_API_KEY|API_AUTH_TOKEN|ANTHROPIC_API_KEY|GEMINI_API_KEY)\s*[:=]\s*['"]?([A-Za-z0-9._~+/=-]{16,})"""
    )),
    ("bearer-token-literal", re.compile(
        r"""(?i)Authorization\s*:\s*Bearer\s+(?!\$\{|<|YOUR\b|EXAMPLE\b|PLACEHOLDER\b|DUMMY\b|REDACTED\b|XXX\b)[A-Za-z0-9._~+/=-]{20,}"""
    )),
]

PLACEHOLDER_FRAGMENTS = (
    "placeholder", "your_", "example", "dummy", "changeme", "replace_me",
    "redacted", "test_token", "xxx", "sample",
)
SENSITIVE_EXACT_NAMES = {
    ".env", "id_rsa", "id_ed25519", "credentials.json", "secrets.json",
}
SENSITIVE_SUFFIXES = {
    ".pem", ".key", ".p12", ".pfx", ".sqlite", ".sqlite3", ".db",
    ".log", ".wav", ".mp3", ".m4a", ".aac", ".ogg",
}
REVIEW_SUFFIXES = {".pdf", ".docx", ".xlsx", ".xls", ".zip", ".tar", ".gz"}
SENSITIVE_PARTS = {
    "uploads", "upload", "recordings", "recording", "patient_data",
    "patient_records", "medical_records", "clinical_data", "case_files",
    "audio_uploads", "runtime_logs",
}
KB_HINTS = ("knowledge_base", "knowledge-base", "psyconsult-community-kb-v1", "mock_data")


def git_paths(args: list[str]) -> set[str]:
    try:
        raw = subprocess.check_output(["git", *args, "-z"], cwd=ROOT, stderr=subprocess.DEVNULL)
        return {x.decode("utf-8", "replace") for x in raw.split(b"\0") if x}
    except Exception:
        return set()


def all_local_files() -> set[Path]:
    files: set[Path] = set()
    for path in ROOT.rglob("*"):
        try:
            rel = path.relative_to(ROOT)
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.is_file():
            files.add(rel)
    return files


def is_placeholder(value: str) -> bool:
    low = value.lower()
    return any(part in low for part in PLACEHOLDER_FRAGMENTS) or low in {"none", "null", "false", "changeme"}


def main() -> int:
    if not (ROOT / ".git").exists():
        print("WARNING: 当前目录未检测到 .git；请在仓库根目录运行。")

    tracked = git_paths(["ls-files", "--cached"])
    local = all_local_files()
    suspicious_paths: list[tuple[str, str]] = []
    secret_hits: list[tuple[str, int, str]] = []

    for rel in sorted(local, key=lambda p: str(p).lower()):
        path = ROOT / rel
        name = path.name.lower()
        parts = {part.lower() for part in rel.parts}
        status = "tracked" if rel.as_posix() in tracked else "local/untracked-or-ignored"

        if (
            name in SENSITIVE_EXACT_NAMES
            or name.endswith(".env") and name != ".env.example"
            or path.suffix.lower() in SENSITIVE_SUFFIXES
            or bool(parts & SENSITIVE_PARTS)
        ):
            suspicious_paths.append((rel.as_posix(), status))
        elif path.suffix.lower() in REVIEW_SUFFIXES:
            suspicious_paths.append((rel.as_posix(), status + "; review file content/rights"))

        if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > MAX_TEXT_BYTES:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for line_no, line in enumerate(text.splitlines(), 1):
            for rule, pattern in SECRET_PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                candidate = match.group(1) if match.lastindex else match.group(0)
                if is_placeholder(candidate):
                    continue
                secret_hits.append((rel.as_posix(), line_no, rule))

    print("=== PsyConsult public-release local audit ===")
    print(f"Root: {ROOT}")
    print(f"Local files inspected by name: {len(local)}")
    print("\n[1] Potential sensitive files (manual review; values not printed)")
    if suspicious_paths:
        for path, status in suspicious_paths:
            print(f"REVIEW | {status} | {path}")
    else:
        print("No file names matched the configured review rules.")

    print("\n[2] Potential secret patterns (values are never printed)")
    if secret_hits:
        for path, line_no, rule in secret_hits:
            print(f"REVIEW | {rule} | {path}:{line_no}")
    else:
        print("No matches for the configured secret patterns.")

    print("\n[3] Knowledge-base inventory / license review")
    kb_roots = [
        p for p in local
        if any(hint in p.as_posix().lower() for hint in KB_HINTS)
    ]
    if not kb_roots:
        print("No matching knowledge-base path detected; inspect repository structure manually.")
    else:
        parent_dirs = sorted({str(Path(p.as_posix()).parent) for p in kb_roots})
        print(f"Matching knowledge-base-related files: {len(kb_roots)}")
        for p in kb_roots[:30]:
            print("KB FILE |", p.as_posix())
        if len(kb_roots) > 30:
            print(f"... {len(kb_roots) - 30} more matching files omitted")
        license_names = [
            p.as_posix() for p in local
            if p.name.lower() in {"license", "license.md", "license.txt", "notice", "notice.md", "copyright"}
        ]
        registry_names = [
            p.as_posix() for p in local
            if p.name.lower() in {"source_registry.csv", "sources.csv", "sources.yml", "sources.yaml"}
        ]
        print("License/NOTICE files:", ", ".join(license_names) if license_names else "none found")
        print("Source registries:", ", ".join(registry_names) if registry_names else "none found")
        print("NOTE | A source URL is not proof of permission to redistribute copied text/images.")

    print("\n[4] Manual checks still required")
    print("- Verify every report, PDF, audio, log, database and screenshot is synthetic or authorized.")
    print("- Verify source licenses, attribution, translation/adaptation terms, and third-party components.")
    print("- Run Gitleaks against both current files and Git history.")
    print("- Re-run tests/build on the exact commit being published.")

    if secret_hits:
        print("\nRESULT: potential secret patterns found; do not publish until reviewed.")
        return 2
    print("\nRESULT: heuristic scan completed; this is not a certification that the repository is safe.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
