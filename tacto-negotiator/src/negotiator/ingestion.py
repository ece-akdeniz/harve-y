"""Versioned public data with explicit conflicts and missing-table diagnostics."""

import hashlib
import json
import sqlite3
from datetime import UTC, datetime

from arena_kit.data import DataPackage


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


class VersionedPackage(DataPackage):
    def __init__(self, root, release=None):
        super().__init__(root, release)
        self.warnings = []
        base = json.loads((self.root / "facts.json").read_text())
        extra = json.loads((self.release / "facts.json").read_text()) if self.release else {}
        for layer in (base, extra):
            if not isinstance(layer, dict) or any(not isinstance(v, dict) for v in layer.values()):
                raise ValueError("facts must map IDs to objects")
        self.conflicts = sorted(k for k in base.keys() & extra.keys() if base[k] != extra[k])
        # Conflicting IDs are unavailable for claims; retain both versions for diagnosis.
        self.conflict_versions = {k: {"base": base[k], "release": extra[k]} for k in self.conflicts}
        for key in self.conflicts:
            self.facts.pop(key, None)
        self.sources = {k: "release" if k in extra else "base" for k in self.facts}
        files = {}
        for label, directory in (("base", self.root), ("release", self.release)):
            if directory:
                files[label] = {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(directory.rglob("*"))
                                if p.is_file() and not p.is_symlink() and
                                (label != "base" or self.release is None or not p.is_relative_to(self.release))}
        self.manifest = {"schema_version": 1, "files": files, "sha256": fingerprint(files),
                         "ingested_at": datetime.now(UTC).isoformat(), "conflicts": self.conflict_versions,
                         "warnings": self.warnings}

    def query(self, sql, params=(), limit=200):
        if self.db is None:
            if "no SQLite database" not in self.warnings:
                self.warnings.append("no SQLite database")
            return []
        try:
            return super().query(sql, params, limit)
        except sqlite3.OperationalError as exc:
            if not str(exc).startswith(("no such table:", "no such column:")):
                raise
            if str(exc) not in self.warnings:
                self.warnings.append(str(exc))
            return []

    def lookup(self, ref):
        return None if ref in self.conflicts else super().lookup(ref)

    def ids(self, prefix):
        return [ref for ref in super().ids(prefix) if ref not in self.conflicts]


def context_manifest(case, package):
    facts = case.get("facts") or {}
    conflicts = sorted(k for k in facts.keys() & package.facts.keys() if facts[k] != package.facts[k])
    return {"schema_version": 1, "data_sha256": package.manifest["sha256"],
            "case_sha256": fingerprint(case), "case_overrides": conflicts,
            "unresolved_release_conflicts": package.conflicts}
