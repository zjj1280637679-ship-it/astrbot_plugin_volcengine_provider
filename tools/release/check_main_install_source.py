#!/usr/bin/env python3
"""Validate the default branch as AstrBot's single installation source."""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_REPO = (
    "https://github.com/zjj1280637679-ship-it/"
    "astrbot_plugin_volcengine_provider"
)
MAX_ARCHIVE_BYTES = 16 * 1024 * 1024

REQUIRED_FILES = (
    "metadata.yaml",
    "main.py",
    "__init__.py",
    "_conf_schema.json",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "logo.png",
    "providers.py",
    "registry.py",
    "adapters/audio.py",
    "adapters/image.py",
    "adapters/limits.py",
    "adapters/video.py",
    "capabilities/cache_insight.py",
    "capabilities/dashboard_asset_bridge.py",
)
REQUIRED_CONFIG_KEYS = {
    "audio_max_mb",
    "audio_transcode_timeout_seconds",
    "video_max_mb",
    "video_transcode_timeout_seconds",
    "image_compress_enabled",
    "image_max_mb",
    "image_compress_max_size",
    "image_compress_quality",
    "cache_log_enabled",
    "cache_log_every",
}
PRODUCTION_PYTHON = (
    "__init__.py",
    "main.py",
    "providers.py",
    "registry.py",
    "adapters",
    "capabilities",
    "compatibility",
    "metadata",
)
FORBIDDEN_PATH_PARTS = {
    ".env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
}
SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{32,}\b"),
}


def fail(message: str) -> None:
    raise SystemExit(f"MAIN_INSTALL_SOURCE_ERROR: {message}")


def yaml_scalar(text: str, key: str) -> str:
    pattern = re.compile(
        rf"^{re.escape(key)}:\s*(?:\"([^\"]*)\"|'([^']*)'|([^#\r\n]*?))\s*(?:#.*)?$",
        re.MULTILINE,
    )
    match = pattern.search(text)
    if match is None:
        fail(f"metadata.yaml is missing root scalar {key!r}")
    return next((value for value in match.groups() if value is not None), "").strip()


def tracked_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        fail(f"cannot enumerate the Git installation source: {exc}")
    return [ROOT / item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def check_metadata() -> str:
    text = (ROOT / "metadata.yaml").read_text(encoding="utf-8")
    values = {
        key: yaml_scalar(text, key)
        for key in ("name", "display_name", "desc", "version", "author", "repo", "astrbot_version")
    }
    if values["name"] != "astrbot_plugin_volcengine_provider":
        fail(f"unexpected plugin name: {values['name']!r}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", values["version"]):
        fail(f"version must be an unsigned three-part release: {values['version']!r}")
    if values["repo"] != EXPECTED_REPO:
        fail(f"repo must be the default repository root: {values['repo']!r}")
    if values["astrbot_version"] != ">=4.26.1":
        fail(f"unexpected AstrBot compatibility range: {values['astrbot_version']!r}")
    for key in ("display_name", "desc", "author"):
        if not values[key]:
            fail(f"metadata field {key!r} must not be empty")
    return values["version"]


def check_required_files() -> None:
    missing = [relative for relative in REQUIRED_FILES if not (ROOT / relative).is_file()]
    if missing:
        fail(f"default main installation source is incomplete: {missing}")


def check_configuration() -> None:
    try:
        schema = json.loads((ROOT / "_conf_schema.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"invalid _conf_schema.json: {exc}")
    if not isinstance(schema, dict):
        fail("_conf_schema.json must contain a JSON object")
    missing = sorted(REQUIRED_CONFIG_KEYS - set(schema))
    if missing:
        fail(f"plugin configuration schema is missing keys: {missing}")


def check_release_ledger(version: str, *, require_releaseable: bool) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    state = json.loads((ROOT / "docs" / "PROJECT_STATE.json").read_text(encoding="utf-8"))
    if version not in readme:
        fail(f"README does not identify version {version}")
    if not re.search(rf"^##\s+{re.escape(version)}(?:\s|$)", changelog, re.MULTILINE):
        fail(f"CHANGELOG has no {version} heading")
    development = state.get("development") or {}
    if str(development.get("version")) != version:
        fail("PROJECT_STATE development.version does not match metadata")
    verdict = state.get("verdict") or {}
    candidate = verdict.get("active_release_candidate")
    state_version = candidate.get("version") if isinstance(candidate, dict) else verdict.get("stable_release")
    if str(state_version) != version:
        fail("PROJECT_STATE candidate/stable release does not match metadata")
    if isinstance(candidate, dict):
        status = candidate.get("status")
        releaseable = candidate.get("releaseable")
        if status not in {"validating", "ready"}:
            fail(f"unsupported candidate status: {status!r}")
        if releaseable is not (status == "ready"):
            fail("candidate status and releaseable flag disagree")
        if development.get("track") != "release_candidate":
            fail("candidate development.track must be release_candidate")
        if development.get("status") != status:
            fail("candidate and development status disagree")
        if development.get("installable") is not releaseable:
            fail("candidate releaseable and development.installable disagree")
        marker = f"| 活跃候选 | **{version}**"
        if marker not in readme:
            fail("README does not project the active candidate state")
        if require_releaseable and not releaseable:
            fail("publication mode requires a ready, releaseable candidate")
    else:
        if verdict.get("stable_status") != "current_stable_release":
            fail("stable PROJECT_STATE must use current_stable_release status")
        if development.get("branch") != "main":
            fail("stable development.branch must be main")
        if development.get("track") != "stable" or development.get("status") != "stable":
            fail("stable development track/status is inconsistent")
        if development.get("installable") is not True:
            fail("stable default-main source must be installable")
        marker = f"| 稳定版本 | **{version}**"
        if marker not in readme:
            fail("README does not project the stable release state")


def check_action_pins() -> None:
    findings: list[str] = []
    workflow_root = ROOT / ".github" / "workflows"
    paths = sorted({*workflow_root.glob("*.yml"), *workflow_root.glob("*.yaml")})
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = re.match(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)", line)
            if match is None:
                continue
            target = match.group(1)
            if target.startswith(("./", "docker://")):
                continue
            if not re.fullmatch(r"[^@]+@[0-9a-fA-F]{40}", target):
                findings.append(f"{path.relative_to(ROOT)}:{line_number}: {target}")
    if findings:
        fail("workflow actions must be pinned to full commit SHAs: " + "; ".join(findings))


def check_logo() -> None:
    header = (ROOT / "logo.png").read_bytes()[:24]
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        fail("logo.png is not a valid PNG header")
    width, height = struct.unpack(">II", header[16:24])
    if width != height or width < 256:
        fail(f"logo.png must be square and at least 256 px: {width}x{height}")


def check_python_syntax() -> None:
    paths: list[Path] = []
    for relative in PRODUCTION_PYTHON:
        path = ROOT / relative
        if path.is_file():
            paths.append(path)
        elif path.is_dir():
            paths.extend(sorted(path.rglob("*.py")))
    for path in paths:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except (OSError, SyntaxError, UnicodeError) as exc:
            fail(f"cannot compile {path.relative_to(ROOT)}: {exc}")


def check_repository_payload(paths: list[Path]) -> int:
    total = 0
    findings: list[str] = []
    for path in paths:
        relative = path.relative_to(ROOT)
        if any(
            part in FORBIDDEN_PATH_PARTS or part.startswith(".env.")
            for part in relative.parts
        ):
            findings.append(f"forbidden tracked path: {relative.as_posix()}")
            continue
        if not path.is_file():
            fail(f"tracked path is missing from the checkout: {relative.as_posix()}")
        size = path.stat().st_size
        total += size
        if size > 2 * 1024 * 1024:
            findings.append(f"unexpected file larger than 2 MiB: {relative.as_posix()}")
        if size <= 2 * 1024 * 1024:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(text):
                    findings.append(f"possible {label}: {relative.as_posix()}")
    if total > MAX_ARCHIVE_BYTES:
        findings.append(f"tracked source is larger than 16 MiB: {total} bytes")
    if findings:
        fail("; ".join(findings))
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-releaseable",
        action="store_true",
        help="reject a validating candidate before publication",
    )
    args = parser.parse_args()
    check_required_files()
    version = check_metadata()
    check_configuration()
    check_release_ledger(version, require_releaseable=args.require_releaseable)
    check_logo()
    check_python_syntax()
    check_action_pins()
    paths = tracked_files()
    total = check_repository_payload(paths)
    print(
        "MAIN_INSTALL_SOURCE_OK "
        f"version={version} tracked_files={len(paths)} uncompressed_bytes={total}"
    )


if __name__ == "__main__":
    main()
