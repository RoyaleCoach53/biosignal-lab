"""Verify a frozen checkout's actual distributions or offline Linux container.

Results are local evidence, never publication. Network is needed for dependency
installation/builds; container runtime checks explicitly disable it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time


class Commands:
    def __init__(self, output: Path, environment: dict):
        self.output, self.environment = output, environment
        self.results = []

    def run(self, name, arguments, *, cwd=None, timeout=1800):
        began = time.monotonic()
        log_path = self.output / (name + ".log")
        with log_path.open("x", encoding="utf-8") as log:
            result = subprocess.run([str(a) for a in arguments], cwd=cwd or self.output,
                                    env=self.environment, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=timeout)
        self.results.append({"name": name, "exit_code": result.returncode,
                             "seconds": time.monotonic() - began})
        print(f"{name}: {result.returncode}", flush=True)
        if result.returncode:
            raise RuntimeError(f"{name} failed with exit {result.returncode}; inspect its local log")
        return log_path.read_text(encoding="utf-8", errors="replace")


def _git(source: Path, *arguments) -> str:
    return subprocess.check_output(["git", *arguments], cwd=source, text=True).strip()


def assert_frozen(source: Path, expected: str):
    if _git(source, "rev-parse", "HEAD") != expected or _git(source, "status", "--porcelain"):
        raise RuntimeError("Source must match the frozen, clean expected commit")


def smoke_result(text):
    records = [line.split("=", 1)[1] for line in text.splitlines()
               if line.startswith("VERIFICATION_JSON=")]
    if len(records) != 1:
        raise ValueError("Expected one complete functional verification record")
    return json.loads(records[0])


def verify_packaging(source, output, python, commands, smoke):
    dist = output / "dist"
    commands.run("build", [python, "-m", "build", "--outdir", dist], cwd=source)
    wheels, sdists = sorted(dist.glob("*.whl")), sorted(dist.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ValueError("Expected one freshly built wheel and source distribution")
    artifacts = wheels + sdists
    verifier = ("import importlib.util,sys; "
                "spec=importlib.util.spec_from_file_location('release',sys.argv[1]); "
                "m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);"
                "[m.verify_archive(__import__('pathlib').Path(p)) for p in sys.argv[2:]]")
    commands.run("archive-preflight", [python, "-c", verifier,
                                       source / "tools/release_artifacts.py", *artifacts])
    results = []
    for index, artifact in enumerate(artifacts):
        target = output / f"isolated-{index}"
        commands.run(f"venv-create-{index}", [python, "-m", "venv", target])
        interpreter = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        commands.run(f"pip-upgrade-{index}", [interpreter, "-m", "pip", "install", "--upgrade", "pip>=26.3"])
        commands.run(f"install-{index}", [interpreter, "-m", "pip", "install", str(artifact) + "[all,formats]"])
        commands.run(f"consistency-{index}", [interpreter, "-m", "pip", "check"])
        checks = smoke_result(commands.run(f"smoke-{index}", [interpreter, "-I", smoke]))
        results.append({"name": artifact.name,
                        "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(), "checks": checks})
        if index == 0:
            commands.run("release-evidence", [interpreter, source / "tools/release_artifacts.py",
                                               "--dist", dist, "--extra", "all", "--extra", "formats"])
    for line in (dist / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        if Path(name).name != name or hashlib.sha256((dist / name).read_bytes()).hexdigest() != digest:
            raise ValueError("Artifact/SBOM checksum verification failed")
    return {"artifacts": results, "checksums_verified": True,
            "sbom_components": len(json.loads((dist / "sbom.cdx.json").read_text())["components"])}


def verify_docker(source, expected, ca_bundle, commands, smoke):
    tag = "biosignal-lab:verify-" + expected[:12]
    arguments = ["docker", "build"]
    if ca_bundle is not None:
        arguments += ["--secret", "id=build_ca,src=" + str(ca_bundle)]
    commands.run("docker-build", [*arguments, "-t", tag, "."], cwd=source)
    text = commands.run("docker-runtime", ["docker", "run", "--rm", "--network", "none",
                        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                        "-v", str(smoke) + ":/tmp/runtime_smoke.py:ro", tag,
                        "python", "/tmp/runtime_smoke.py", "--container"])
    image = subprocess.check_output(["docker", "image", "inspect", tag,
                                     "--format", "{{.Id}}"], text=True).strip()
    return {"checks": smoke_result(text), "image_id": image}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--python", default=sys.executable,
                        help="Interpreter with the build module installed (default: this interpreter)")
    parser.add_argument("--output", type=Path, required=True, help="New local results directory")
    parser.add_argument("--expected-commit", required=True, help="Full frozen HEAD commit SHA")
    parser.add_argument("--mode", choices=("packaging", "docker"), required=True)
    parser.add_argument("--ca-bundle", type=Path,
                        help="Optional approved TLS inspection CA bundle, mounted only during Docker build")
    parser.add_argument("--cache-dir", type=Path, help="Optional writable dependency cache; otherwise inside output")
    args = parser.parse_args(argv)
    source, output = args.source.resolve(), args.output.resolve()
    ca_bundle = args.ca_bundle.resolve() if args.ca_bundle else None
    if ca_bundle is not None and not ca_bundle.is_file():
        parser.error("--ca-bundle must be an existing approved certificate bundle")
    assert_frozen(source, args.expected_commit)
    output.mkdir(parents=True, exist_ok=False)
    cache = args.cache_dir.resolve() if args.cache_dir else output / "cache"
    cache.mkdir(parents=True, exist_ok=True)
    environment = {k: v for k, v in os.environ.items()
                   if k not in {"PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "PIP_TARGET", "PIP_PREFIX", "PIP_USER"}}
    environment.update(PIP_CACHE_DIR=str(cache / "pip"), XDG_CACHE_HOME=str(cache),
                       MPLCONFIGDIR=str(cache / "matplotlib"), PYTHONNOUSERSITE="1",
                       STREAMLIT_BROWSER_GATHER_USAGE_STATS="false")
    smoke = Path(__file__).with_name("runtime_smoke.py").resolve()
    commands = Commands(output, environment)
    report = {"source_commit": args.expected_commit, "mode": args.mode, "passed": False,
              "host": {"system": platform.system(), "python": platform.python_version()},
              "installed_extras": ["all", "formats"],
              "optional_checks_not_claimed": ["neural torch in isolated artifacts",
                                               "physical acquisition/native Live extras",
                                               "NeuroKit optional peripheral extra"],
              "helper_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (Path(__file__).resolve(), smoke)},
              "scope": "Actual isolated artifacts or offline Linux container and synthetic workflows; no publication, physical hardware or independent human review"}
    try:
        if args.mode == "packaging":
            report.update(verify_packaging(source, output, args.python, commands, smoke))
        else:
            report.update(verify_docker(source, args.expected_commit, ca_bundle, commands, smoke))
        assert_frozen(source, args.expected_commit)
        report["passed"] = True
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        report["failure"] = {"type": type(exc).__name__, "reason": str(exc)}
        print(f"Verification failed: {exc}", file=sys.stderr)
    finally:
        report["commands"] = commands.results
        with (output / "report.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
            stream.write("\n")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
