"""Verify archives, emit SHA-256 sums and a metadata-based CycloneDX inventory.

Run after building into a NEW directory. Existing evidence is never overwritten.
The SBOM describes the installed dependency closure, not bundled native libraries
or an independent license/legal or vulnerability audit.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
from importlib import metadata
import io
import json
from pathlib import Path, PurePosixPath
import stat
import tarfile
import zipfile

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name


def safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def verify_archive(path: Path):
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)) or not all(safe_member(n) for n in names):
                raise ValueError("Duplicate or unsafe wheel members")
            if any(stat.S_ISLNK(info.external_attr >> 16) for info in archive.infolist()):
                raise ValueError("Wheel contains symbolic links")
            if archive.testzip() is not None:
                raise ValueError("Wheel CRC verification failed")
            records = [n for n in names if n.endswith(".dist-info/RECORD")]
            if len(records) != 1:
                raise ValueError("Wheel must contain one RECORD")
            rows = list(csv.reader(io.StringIO(archive.read(records[0]).decode("utf-8"))))
            if any(len(row) != 3 for row in rows):
                raise ValueError("Malformed wheel RECORD")
            if len(rows) != len({row[0] for row in rows}):
                raise ValueError("Duplicate wheel RECORD row")
            indexed = {row[0]: row[1:] for row in rows}
            for name in names:
                if name.endswith("/"):
                    continue
                if name not in indexed:
                    raise ValueError("Wheel member missing from RECORD")
                digest, size = indexed[name]
                if name == records[0] or name.endswith(("/RECORD.jws", "/RECORD.p7s")):
                    continue
                content = archive.read(name)
                expected = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
                if digest != expected or size != str(len(content)):
                    raise ValueError("Wheel RECORD hash/size mismatch")
            if any(n not in names for n in indexed):
                raise ValueError("RECORD references absent member")
    elif path.name.endswith(".tar.gz"):
        with tarfile.open(path, "r:gz") as archive:
            members = archive.getmembers()
            names = [m.name for m in members]
            if len(names) != len(set(names)) or not all(safe_member(n) for n in names):
                raise ValueError("Duplicate or unsafe source-distribution members")
            if any(not (m.isfile() or m.isdir()) for m in members):
                raise ValueError("Source distribution contains links or special files")
            if len({PurePosixPath(n).parts[0] for n in names}) != 1:
                raise ValueError("Source distribution must have one root")
    else:
        raise ValueError("Expected a wheel or .tar.gz source distribution")


def dependency_inventory(extras=()):
    pending = [("biosignal-lab", tuple(extras))]
    components, visited, dependencies = [], set(), []
    while pending:
        requested, selected_extras = pending.pop()
        name = canonicalize_name(requested)
        if (name, selected_extras) in visited:
            continue
        visited.add((name, selected_extras))
        distribution = metadata.distribution(name)
        meta = distribution.metadata
        ref = f"pkg:pypi/{name}@{distribution.version}"
        if not any(c["bom-ref"] == ref for c in components):
            license_expression = meta.get("License-Expression")
            declared_license = meta.get("License", "NOASSERTION")
            if len(declared_license) > 160 or "\n" in declared_license:
                declared_license = "NOASSERTION (see distribution license files)"
            component = {"type": "library", "bom-ref": ref, "name": name,
                         "version": distribution.version, "purl": ref,
                         "properties": [{"name": "biosignal:declared-license", "value": declared_license},
                                        {"name": "biosignal:license-files", "value": json.dumps(meta.get_all("License-File") or [])}]}
            if license_expression:
                component["licenses"] = [{"expression": license_expression}]
            components.append(component)
        children = set()
        for text in distribution.requires or []:
            requirement = Requirement(text)
            if requirement.marker and not any(requirement.marker.evaluate({"extra": e}) for e in ("", *selected_extras)):
                continue
            child = metadata.distribution(requirement.name)
            children.add(f"pkg:pypi/{canonicalize_name(requirement.name)}@{child.version}")
            pending.append((requirement.name, tuple(sorted(requirement.extras))))
        previous = next((d for d in dependencies if d["ref"] == ref), None)
        if previous:
            previous["dependsOn"] = sorted(set(previous["dependsOn"]) | children)
        else:
            dependencies.append({"ref": ref, "dependsOn": sorted(children)})
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"properties": [{"name": "biosignal:scope", "value": "Installed Python distribution metadata and selected extras; not an advisory scan or bundled-native license audit"}]},
            "components": sorted(components, key=lambda c: c["name"]),
            "dependencies": sorted(dependencies, key=lambda d: d["ref"])}


def write_new(path, text):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def prepare(folder: Path, extras=()):
    paths = sorted(p for p in folder.iterdir() if p.name.endswith((".whl", ".tar.gz")))
    if not paths or not any(p.suffix == ".whl" for p in paths) or not any(p.name.endswith(".tar.gz") for p in paths):
        raise ValueError("Build both a wheel and source distribution first")
    outputs = [folder / "SHA256SUMS", folder / "sbom.cdx.json"]
    if any(p.exists() or p.is_symlink() for p in outputs):
        raise FileExistsError("Use a fresh output directory; existing release evidence is preserved")
    for path in paths:
        if path.is_symlink():
            raise ValueError("Release artifacts must be regular files")
        verify_archive(path)
    inventory = dependency_inventory(extras)
    sbom_text = json.dumps(inventory, indent=2, allow_nan=False) + "\n"
    sums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}" for p in paths]
    sums.append(f"{hashlib.sha256(sbom_text.encode()).hexdigest()}  sbom.cdx.json")
    write_new(outputs[1], sbom_text)
    write_new(outputs[0], "\n".join(sums) + "\n")
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--extra", action="append", default=[])
    args = parser.parse_args()
    try:
        paths = prepare(args.dist, args.extra)
    except (ValueError, OSError, zipfile.BadZipFile, tarfile.TarError, metadata.PackageNotFoundError) as exc:
        parser.exit(1, f"Release verification failed: {type(exc).__name__}; no release approval implied.\n")
    print(f"Verified {len(paths)} archives; wrote SHA256SUMS and sbom.cdx.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
