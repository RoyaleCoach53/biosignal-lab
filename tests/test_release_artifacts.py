"""Archive verification catches corrupt payloads before release evidence is emitted."""
import base64
import hashlib
import io
import tarfile
import zipfile

import pytest
from tools.release_artifacts import verify_archive, prepare, safe_member


def wheel(path, payload=b"original", recorded=b"original"):
    digest = base64.urlsafe_b64encode(hashlib.sha256(recorded).digest()).rstrip(b"=").decode()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("example/__init__.py", payload)
        archive.writestr("example-1.dist-info/RECORD", f"example/__init__.py,sha256={digest},{len(recorded)}\nexample-1.dist-info/RECORD,,\n")


def test_wheel_record_corruption_is_rejected(tmp_path):
    path = tmp_path / "example.whl"
    wheel(path)
    verify_archive(path)
    wheel(path, payload=b"tampered")
    with pytest.raises(ValueError, match="hash/size"):
        verify_archive(path)


@pytest.mark.parametrize("name", ["../secret", "/absolute", "root/../../secret", "root\\secret"])
def test_unsafe_archive_paths(name):
    assert not safe_member(name)


def test_sdist_symlinks_are_rejected(tmp_path):
    path = tmp_path / "example.tar.gz"
    with tarfile.open(path, "w:gz") as archive:
        member = tarfile.TarInfo("example/link")
        member.type = tarfile.SYMTYPE
        member.linkname = "/etc/passwd"
        archive.addfile(member)
    with pytest.raises(ValueError, match="links"):
        verify_archive(path)


def test_existing_release_evidence_is_preserved(tmp_path):
    wheel(tmp_path / "example.whl")
    (tmp_path / "example.tar.gz").write_bytes(b"unused")
    marker = tmp_path / "SHA256SUMS"
    marker.write_text("previous release")
    with pytest.raises(FileExistsError):
        prepare(tmp_path)
    assert marker.read_text() == "previous release"
