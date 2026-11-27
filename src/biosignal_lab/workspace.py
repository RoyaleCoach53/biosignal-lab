"""Local JSON projects with immutable document revisions. Never load executable objects."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4


class Workspace:
    """An explicitly selected local root; recordings are not copied into projects.

    Documents are bounded JSON objects. Each save creates a new revision using an
    exclusive filesystem link, so concurrent saves cannot overwrite prior work.
    This is a single-user local store, not an authorization boundary for a server.
    """

    def __init__(self, root: str | Path, max_document_bytes: int = 2_000_000):
        if not isinstance(max_document_bytes, int) or max_document_bytes < 1:
            raise ValueError("Document size limit must be positive")
        candidate = Path(root).absolute()
        if candidate.is_symlink():
            raise ValueError("Workspace root must not be a symlink")
        candidate.mkdir(parents=True, exist_ok=True)
        self.root = candidate.resolve()
        self.max_document_bytes = max_document_bytes

    @staticmethod
    def _name(value: str) -> str:
        if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", value):
            raise ValueError("Use a 1–64 character identifier containing letters, digits, _ or -")
        return value

    def _project(self, project: str) -> Path:
        path = self.root / self._name(project)
        if path.is_symlink() or not path.is_dir():
            raise ValueError("Unknown project or unsafe project path")
        return path

    def create_project(self, title: str) -> str:
        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise ValueError("Project title must contain 1–200 characters")
        project = uuid4().hex
        (self.root / project).mkdir(mode=0o700)
        self.save(project, "project", {"schema_version": 1, "title": title.strip()})
        return project

    def save(self, project: str, document: str, payload: dict) -> int:
        path = self._project(project)
        name = self._name(document)
        if not isinstance(payload, dict):
            raise ValueError("Document must be a JSON object")
        encoded = (json.dumps(payload, ensure_ascii=False, allow_nan=False,
                              sort_keys=True, indent=2) + "\n").encode("utf-8")
        if len(encoded) > self.max_document_bytes:
            raise ValueError("Document exceeds the configured byte limit")
        fd, temp = tempfile.mkstemp(prefix=".save-", dir=path)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            revision = max(self.revisions(project, name), default=0) + 1
            while True:
                target = path / f"{name}.{revision:08d}.json"
                try:
                    os.link(temp, target)
                    return revision
                except FileExistsError:
                    revision += 1
        finally:
            Path(temp).unlink(missing_ok=True)

    def revisions(self, project: str, document: str) -> list[int]:
        path = self._project(project)
        name = self._name(document)
        pattern = re.compile(re.escape(name) + r"\.([0-9]{8,})\.json")
        return sorted(int(match.group(1)) for file in path.iterdir()
                      if (match := pattern.fullmatch(file.name)) and file.is_file()
                      and not file.is_symlink())

    def load(self, project: str, document: str, revision: int | None = None) -> dict:
        path = self._project(project)
        name = self._name(document)
        if revision is None:
            revisions = self.revisions(project, name)
            if not revisions:
                raise FileNotFoundError(f"No saved document: {name}")
            revision = revisions[-1]
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise ValueError("Revision must be a positive integer")
        target = path / f"{name}.{revision:08d}.json"
        fd = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        with os.fdopen(fd, "rb") as stream:
            if target.is_symlink():
                raise ValueError("Document symlinks are unsupported")
            data = stream.read(self.max_document_bytes + 1)
        if len(data) > self.max_document_bytes:
            raise ValueError("Document exceeds the configured byte limit")
        payload = json.loads(data, parse_constant=lambda value: _invalid_constant(value))
        if not isinstance(payload, dict):
            raise ValueError("Saved document is not a JSON object")
        return payload

    def projects(self) -> list[dict]:
        found = []
        for path in sorted(self.root.iterdir()):
            if path.is_symlink() or not path.is_dir() or not re.fullmatch(r"[0-9a-f]{32}", path.name):
                continue
            try:
                meta = self.load(path.name, "project")
                found.append({"id": path.name, "title": meta["title"]})
            except (OSError, ValueError, KeyError):
                # Corrupt projects remain on disk for manual recovery.
                continue
        return found


def _invalid_constant(value: str):
    raise ValueError(f"Nonfinite JSON constant: {value}")
