"""Immutable releases with an atomic current-version pointer."""
import hashlib
import json
import os
from pathlib import Path
from uuid import uuid4


def checksum(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def publish(candidate, root):
    candidate, root = Path(candidate), Path(root)
    files = {path.name: checksum(path) for path in candidate.iterdir() if path.is_file()}
    (candidate / "manifest.json").write_text(json.dumps(files, indent=2), encoding="utf-8")
    pointer = {"version": candidate.name, "relative_path": candidate.relative_to(root).as_posix()}
    temporary = root / f".current-{uuid4().hex}.json"
    temporary.write_text(json.dumps(pointer), encoding="utf-8")
    os.replace(temporary, root / "current.json")
    return pointer


def resolve_release(root):
    root = Path(root).resolve()
    pointer = root / "current.json"
    if not pointer.exists():
        return root
    value = json.loads(pointer.read_text(encoding="utf-8"))
    release = (root / value["relative_path"]).resolve()
    if not release.is_relative_to(root):
        raise ValueError("Đường dẫn phiên bản model không hợp lệ")
    manifest = json.loads((release / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest.items():
        path = (release / name).resolve()
        if path.parent != release or checksum(path) != expected:
            raise ValueError(f"Artifact không toàn vẹn: {name}")
    return release
