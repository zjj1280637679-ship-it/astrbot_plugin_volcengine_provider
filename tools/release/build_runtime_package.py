#!/usr/bin/env python3
"""Build and verify the minimal AstrBot runtime distribution.

This script is development tooling. It is intentionally excluded from the
runtime branch/package it produces.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIST_ROOT = ROOT / "dist" / "runtime"
PACKAGE_NAME = "astrbot_plugin_volcengine_provider"
PACKAGE_DIR = DIST_ROOT / PACKAGE_NAME
ZIP_PATH = ROOT / "dist" / f"{PACKAGE_NAME}-runtime.zip"
MANIFEST_PATH = ROOT / "dist" / "runtime-manifest.json"

ROOT_FILES = (
    "metadata.yaml",
    "__init__.py",
    "main.py",
    "providers.py",
    "registry.py",
    "logo.png",
    "LICENSE",
)
RUNTIME_PACKAGES = (
    "adapters",
    "capabilities",
    "compatibility",
    "metadata",
)

# This plugin's runtime is small Python source + logo. AstrBot's public market
# maximum is higher; this tighter project budget catches accidental repository
# packaging before it reaches users.
MAX_RUNTIME_BYTES = 2 * 1024 * 1024
EXPECTED_VERSION = "0.1.19"
EXPECTED_REPO_SUFFIX = "/tree/runtime"

FORBIDDEN_TOP_LEVEL = {
    ".git",
    ".github",
    "tests",
    "docs",
    "evidence",
    "governance",
    "strategy",
    "model_cards",
    "assets",
    "tools",
    "dist",
}
FORBIDDEN_FILENAMES = {
    ".env",
    ".env.local",
    "secrets.json",
    "credentials.json",
}

# High-confidence patterns only. Generic words such as "api_key" are legitimate
# source identifiers and are not themselves secrets.
SECRET_PATTERNS = {
    "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "openai_style_key": re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "bearer_literal": re.compile(rb"Bearer\s+[A-Za-z0-9._~+/-]{24,}={0,2}"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


def metadata_scalar(text: str, key: str) -> str:
    match = re.search(
        rf"(?m)^\s*{re.escape(key)}\s*:\s*[\"']?([^\"'\r\n#]+)",
        text,
    )
    return match.group(1).strip() if match else ""


def copy_runtime() -> None:
    shutil.rmtree(ROOT / "dist", ignore_errors=True)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)

    for relative in ROOT_FILES:
        source = ROOT / relative
        if not source.is_file():
            raise RuntimeError(f"required runtime file is missing: {relative}")
        shutil.copy2(source, PACKAGE_DIR / relative)

    for package in RUNTIME_PACKAGES:
        source_dir = ROOT / package
        target_dir = PACKAGE_DIR / package
        if not source_dir.is_dir():
            raise RuntimeError(f"required runtime package is missing: {package}")
        target_dir.mkdir(parents=True, exist_ok=True)
        python_files = sorted(source_dir.glob("*.py"))
        if not python_files:
            raise RuntimeError(f"runtime package has no Python files: {package}")
        for source in python_files:
            shutil.copy2(source, target_dir / source.name)


def verify_inventory() -> list[Path]:
    files = sorted(path for path in PACKAGE_DIR.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError("runtime package is empty")

    for path in files:
        relative = path.relative_to(PACKAGE_DIR)
        if relative.parts[0] in FORBIDDEN_TOP_LEVEL:
            raise RuntimeError(f"development path leaked into runtime: {relative}")
        if path.name in FORBIDDEN_FILENAMES:
            raise RuntimeError(f"sensitive filename leaked into runtime: {relative}")
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            raise RuntimeError(f"cache/build output leaked into runtime: {relative}")

    total_bytes = sum(path.stat().st_size for path in files)
    if total_bytes > MAX_RUNTIME_BYTES:
        raise RuntimeError(
            f"runtime package unexpectedly large: {total_bytes} > {MAX_RUNTIME_BYTES} bytes"
        )

    metadata_text = (PACKAGE_DIR / "metadata.yaml").read_text(encoding="utf-8")
    version = metadata_scalar(metadata_text, "version")
    repo = metadata_scalar(metadata_text, "repo")
    if version != EXPECTED_VERSION:
        raise RuntimeError(f"metadata version must be {EXPECTED_VERSION}, got {version!r}")
    if not repo.endswith(EXPECTED_REPO_SUFFIX):
        raise RuntimeError(f"metadata repo must point at runtime branch, got {repo!r}")

    return files


def scan_secrets(files: list[Path]) -> None:
    findings: list[str] = []
    for path in files:
        # Binary runtime assets are allowed but private-key signatures are still
        # checked in their bytes. Other textual key formats are intentionally
        # high-confidence to avoid false positives on source identifiers.
        data = path.read_bytes()
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                findings.append(f"{path.relative_to(PACKAGE_DIR)}:{label}")
    if findings:
        raise RuntimeError("possible secret material in runtime artifact: " + ", ".join(findings))


def build_zip(files: list[Path]) -> None:
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(PACKAGE_DIR)
            archive.write(path, Path(PACKAGE_NAME) / relative)


def write_manifest(files: list[Path]) -> None:
    entries = []
    for path in files:
        relative = path.relative_to(PACKAGE_DIR).as_posix()
        data = path.read_bytes()
        entries.append(
            {
                "path": relative,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    payload = {
        "schema_version": 1,
        "package": PACKAGE_NAME,
        "version": EXPECTED_VERSION,
        "file_count": len(entries),
        "uncompressed_bytes": sum(item["bytes"] for item in entries),
        "zip_bytes": ZIP_PATH.stat().st_size,
        "files": entries,
    }
    MANIFEST_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    copy_runtime()
    files = verify_inventory()
    scan_secrets(files)
    build_zip(files)
    write_manifest(files)
    print(f"RUNTIME_PACKAGE_OK version={EXPECTED_VERSION} files={len(files)} zip={ZIP_PATH.stat().st_size}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RUNTIME_PACKAGE_ERROR: {exc}", file=sys.stderr)
        raise
