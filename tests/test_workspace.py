from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from biosignal_lab.workspace import Workspace


def test_project_recovery_and_concurrent_immutable_revisions(tmp_path):
    store = Workspace(tmp_path / "projects")
    project = store.create_project("Experiment alpha")
    with ThreadPoolExecutor(max_workers=4) as pool:
        revisions = list(pool.map(lambda n: store.save(project, "workflow", {"run": n}), range(12)))
    assert sorted(revisions) == list(range(1, 13))
    restored = Workspace(tmp_path / "projects")
    assert restored.projects() == [{"id": project, "title": "Experiment alpha"}]
    assert {restored.load(project, "workflow", n)["run"] for n in revisions} == set(range(12))
    assert restored.load(project, "workflow") == restored.load(project, "workflow", 12)


def test_workspace_bounds_traversal_and_nonfinite(tmp_path):
    store = Workspace(tmp_path, max_document_bytes=200)
    project = store.create_project("Test")
    for name in ("../escape", "/absolute", "a/b", "", "a.b"):
        with pytest.raises(ValueError):
            store.save(project, name, {})
    for payload in ({"bad": float("nan")}, {"big": "a" * 300}, [1]):
        with pytest.raises(ValueError):
            store.save(project, "workflow", payload)
    with pytest.raises(ValueError):
        store.load(project, "workflow", -1)
    assert not list(tmp_path.glob(".save-*"))


def test_symlinks_and_corrupted_documents_are_not_loaded(tmp_path):
    store = Workspace(tmp_path / "projects")
    project = store.create_project("Test")
    outside = tmp_path / "outside.json"
    outside.write_text('{"private": true}')
    target = store.root / project / "workflow.00000001.json"
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("OS does not permit symlink creation")
    assert store.revisions(project, "workflow") == []
    with pytest.raises((OSError, ValueError)):
        store.load(project, "workflow", 1)
    target.unlink()
    target.write_text('{"invalid": NaN}')
    with pytest.raises(ValueError):
        store.load(project, "workflow", 1)
    (store.root / project / "project.00000001.json").write_text("broken json")
    assert store.projects() == []
    assert json.loads(outside.read_text()) == {"private": True}
