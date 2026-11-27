"""Explicit-license dataset manifests and opt-in, checksum-verified local caching."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, build_opener


@dataclass(frozen=True)
class DatasetRecord:
    path: str
    url: str
    sha256: str
    subject: str
    split: str

    def __post_init__(self):
        path = PurePosixPath(self.path)
        if not self.path or "\\" in self.path or ":" in self.path or path.is_absolute() or any(p in {"..", "."} for p in self.path.split("/")) or str(path) != self.path:
            raise ValueError("Record path must be a normalized relative POSIX path")
        parsed = urlsplit(self.url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise ValueError("Dataset URL requires credential-free HTTPS without a fragment")
        if not re.fullmatch("[a-f0-9]{64}", self.sha256):
            raise ValueError("Require a lowercase SHA-256 digest from an authoritative source")
        if not isinstance(self.subject, str) or not self.subject or self.split not in {"train", "validation", "test"}:
            raise ValueError("Require subject identifier and train/validation/test split")


@dataclass(frozen=True)
class DatasetManifest:
    name: str
    version: str
    license_id: str
    license_url: str
    records: tuple[DatasetRecord, ...]

    def __post_init__(self):
        if any(not isinstance(x, str) or not x.strip() for x in (self.name, self.version, self.license_id)):
            raise ValueError("Dataset name, version and license identifier are required")
        license_url = urlsplit(self.license_url)
        if license_url.scheme != "https" or not license_url.hostname or license_url.username or license_url.password:
            raise ValueError("Require a credential-free HTTPS license URL")
        records = tuple(self.records)
        if not records or any(not isinstance(r, DatasetRecord) for r in records):
            raise ValueError("Require validated DatasetRecord entries")
        if len({r.path.casefold() for r in records}) != len(records):
            raise ValueError("Duplicate or case-colliding record paths")
        subjects = {}
        for record in records:
            if record.subject in subjects and subjects[record.subject] != record.split:
                raise ValueError("Subject crosses predefined training/validation/test splits")
            subjects[record.subject] = record.split
        object.__setattr__(self, "records", records)

    @property
    def digest(self):
        value = {"name": self.name, "version": self.version, "license_id": self.license_id,
                 "license_url": self.license_url, "records": [r.__dict__ for r in self.records]}
        return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _hash(path, limit):
    size, digest = 0, sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            size += len(block)
            if size > limit:
                raise ValueError("Dataset record exceeds configured byte limit")
            digest.update(block)
    return digest.hexdigest()


class _HTTPSOnlyRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, newurl):
        destination = urlsplit(newurl)
        if destination.scheme != "https" or not destination.hostname or destination.username or destination.password:
            raise ValueError("Dataset redirects must retain credential-free HTTPS")
        return super().redirect_request(request, response, code, message, headers, newurl)


def _open_https(url, timeout):
    # Reject downgrade before urllib can follow it, rather than merely checking
    # the final response after an insecure request has already been transmitted.
    return build_opener(_HTTPSOnlyRedirect()).open(url, timeout=timeout)


def fetch_record(record: DatasetRecord, cache, *, download=False, license_accepted=False,
                 max_bytes=256 * 1024 * 1024, timeout=30):
    """Return verified cached path; download requires explicit license acceptance.

    No discovery claim, license adjudication or human data is bundled. The caller
    must review source terms and the intended cohort. Cache outside repositories.
    A corrupt existing record raises instead of being silently overwritten.
    """
    if not isinstance(record, DatasetRecord):
        raise TypeError("record must be a DatasetRecord")
    if not isinstance(max_bytes, int) or max_bytes < 1 or not 0 < timeout <= 300:
        raise ValueError("Positive byte limit and timeout up to 300 seconds required")
    selected_root = Path(cache)
    if any(component.is_symlink() for component in (selected_root, *selected_root.parents)):
        raise ValueError("Dataset cache root must not traverse symlinks")
    root = selected_root.resolve()
    destination = root / record.path
    # Resolve every component; reject symlinks, including a dangling final link.
    for component in (destination, *destination.parents):
        if component == root.parent:
            break
        if component.is_symlink():
            raise ValueError("Dataset cache paths must not traverse symlinks")
    if not destination.resolve().is_relative_to(root):
        raise ValueError("Cache path escapes root")
    if destination.exists():
        if not destination.is_file() or _hash(destination, max_bytes) != record.sha256:
            raise ValueError("Cached record fails integrity; existing data preserved")
        return destination
    if not download:
        raise FileNotFoundError("Record absent from cache; network access is opt-in")
    if not license_accepted:
        raise ValueError("Read and explicitly accept the source license before downloading")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Stage beside destination to keep verified creation on one filesystem.
    with tempfile.TemporaryFile(dir=destination.parent) as staged:
        digest, count = sha256(), 0
        with _open_https(record.url, timeout=timeout) as response:
            if urlsplit(response.url).scheme != "https":
                raise ValueError("Dataset redirects must retain HTTPS")
            while block := response.read(min(1024 * 1024, max_bytes + 1 - count)):
                count += len(block)
                if count > max_bytes:
                    raise ValueError("Download exceeds configured byte limit")
                digest.update(block)
                staged.write(block)
        if digest.hexdigest() != record.sha256:
            raise ValueError("Downloaded SHA-256 mismatch; no record installed")
        staged.seek(0)
        created = False
        try:
            with destination.open("xb") as target:
                created = True
                while block := staged.read(1024 * 1024):
                    target.write(block)
        except BaseException:
            if created:
                destination.unlink(missing_ok=True)
            raise
    return destination
