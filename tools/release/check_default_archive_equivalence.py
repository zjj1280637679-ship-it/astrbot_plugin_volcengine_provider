#!/usr/bin/env python3
"""Prove that the default-branch export equals the allow-list runtime package.

AstrBot Cloud was observed freezing the repository default-branch archive,
while direct AstrBot installs use the generated ``runtime`` branch.  The two
surfaces must therefore contain the same paths and bytes before publication.
"""

from __future__ import annotations

import hashlib
import io
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "dist" / "runtime" / "astrbot_plugin_volcengine_provider"


def digest(files: dict[str, bytes]) -> str:
    value = hashlib.sha256()
    for path in sorted(files):
        data = files[path]
        value.update(path.encode("utf-8"))
        value.update(b"\0")
        value.update(str(len(data)).encode("ascii"))
        value.update(b"\0")
        value.update(hashlib.sha256(data).digest())
    return value.hexdigest()


def default_archive_files() -> dict[str, bytes]:
    archive = subprocess.run(
        ["git", "archive", "--format=tar", "HEAD"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    files: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
        for member in bundle.getmembers():
            if not member.isfile():
                continue
            stream = bundle.extractfile(member)
            if stream is None:
                raise RuntimeError(f"cannot read archive member: {member.name}")
            files[member.name] = stream.read()
    return files


def runtime_files() -> dict[str, bytes]:
    if not PACKAGE_DIR.is_dir():
        raise RuntimeError("runtime package missing; run build_runtime_package.py first")
    return {
        path.relative_to(PACKAGE_DIR).as_posix(): path.read_bytes()
        for path in PACKAGE_DIR.rglob("*")
        if path.is_file()
    }


def main() -> int:
    archive = default_archive_files()
    runtime = runtime_files()
    only_archive = sorted(set(archive) - set(runtime))
    only_runtime = sorted(set(runtime) - set(archive))
    changed = sorted(
        path for path in set(archive).intersection(runtime)
        if archive[path] != runtime[path]
    )
    if only_archive or only_runtime or changed:
        raise RuntimeError(
            "default archive/runtime mismatch: "
            f"only_archive={only_archive} only_runtime={only_runtime} changed={changed}"
        )
    print(
        "DEFAULT_ARCHIVE_EQUIVALENCE_OK "
        f"files={len(runtime)} canonical_sha256={digest(runtime)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
