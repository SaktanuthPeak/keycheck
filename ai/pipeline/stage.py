"""Stage runner for the single-notebook pipeline (docs/qwertz-notebook-pipeline-plan.md §4.2, §4.3).

A stage is skipped when its output folder holds a `_DONE.json` whose fingerprint matches
hash(config subset, upstream fingerprints, stage code version). Q7 can never be forced.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

DONE = "_DONE.json"
LOCKED_STAGES = {"q7_test"}


def _canon(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def fingerprint(config: Any, upstream: Iterable[str] = (), code_version: str = "") -> str:
    payload = _canon({"config": config, "upstream": list(upstream), "code": code_version})
    return hashlib.sha256(payload.encode()).hexdigest()


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class StageResult:
    name: str
    out_dir: Path
    fingerprint: str
    summary: dict
    skipped: bool


class StageError(RuntimeError):
    pass


def read_done(out_dir: Path) -> dict | None:
    p = Path(out_dir) / DONE
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def run_stage(
    name: str,
    fn: Callable[[Path], dict],
    *,
    root: str | Path,
    config: Any,
    upstream: Iterable[StageResult | str] = (),
    code_version: str = "",
    force: Iterable[str] = (),
    enabled: bool = True,
) -> StageResult | None:
    """Run `fn(out_dir) -> summary` unless a matching result exists.

    `fn` writes its outputs under out_dir; run_stage adds summary.json and _DONE.json.
    Training stages should keep their own checkpoints under out_dir and resume from them
    when `fn` is called again (the _DONE marker is only written once `fn` returns).
    """
    if not enabled:
        return None
    force = set(force)
    if name in LOCKED_STAGES and name in force:
        raise StageError(f"{name} is locked and does not accept FORCE")
    ups = [u.fingerprint if isinstance(u, StageResult) else str(u) for u in upstream]
    fp = fingerprint(config, ups, code_version)
    out_dir = Path(root) / name
    out_dir.mkdir(parents=True, exist_ok=True)
    done = read_done(out_dir)
    if name in LOCKED_STAGES and done is not None:
        raise StageError(f"{name} already ran once ({out_dir / DONE}); it never re-runs")
    if done and done.get("fingerprint") == fp and name not in force:
        summary = json.loads((out_dir / "summary.json").read_text())
        print(f"[{name}] skipped — up to date ({fp[:8]})")
        return StageResult(name, out_dir, fp, summary, True)
    if done:
        (out_dir / DONE).unlink()
    t0 = time.time()
    print(f"[{name}] running ({fp[:8]})")
    summary = fn(out_dir) or {}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    (out_dir / DONE).write_text(
        json.dumps({"fingerprint": fp, "seconds": round(time.time() - t0, 1), "finished": time.strftime("%FT%T")}, indent=1)
    )
    print(f"[{name}] done in {time.time() - t0:.0f}s")
    return StageResult(name, out_dir, fp, summary, False)


def check_q7_guard(
    *,
    run_final_test: bool,
    mode: str,
    repo_dir: str | Path,
    repo_ref: str,
    q6_hashes: dict[str, str],
    committed_hashes: dict[str, str],
    q7_dir: str | Path,
) -> list[str]:
    """Return the list of unmet Q7 conditions (empty = allowed). Plan §4.3."""
    problems: list[str] = []
    if not run_final_test:
        problems.append("RUN_FINAL_TEST is not True")
    if mode != "full":
        problems.append(f"MODE is {mode!r}, must be 'full'")
    try:
        dirty = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=repo_dir,
                               capture_output=True, text=True, check=True).stdout.strip()
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True).stdout.strip()
        if dirty:
            problems.append("repo has uncommitted changes")
        if not repo_ref or not head.startswith(repo_ref):
            problems.append(f"REPO_REF {repo_ref!r} != checked-out commit {head[:10]}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        problems.append("cannot read git state")
    for key, val in q6_hashes.items():
        if committed_hashes.get(key) != val:
            problems.append(f"hash mismatch for {key}")
    for key in committed_hashes:
        if key not in q6_hashes:
            problems.append(f"missing Q6 hash for {key}")
    if (Path(q7_dir) / DONE).exists():
        problems.append("q7_test/_DONE.json already exists")
    return problems


def code_version(*paths: str | Path) -> str:
    """Hash of the source files a stage depends on, so editing the code re-runs the stage."""
    h = hashlib.sha256()
    for p in sorted(map(str, paths)):
        pp = Path(p)
        files = sorted(pp.rglob("*.py")) if pp.is_dir() else [pp]
        for f in files:
            if f.exists():
                h.update(str(f.name).encode())
                h.update(f.read_bytes())
    return h.hexdigest()[:16]
