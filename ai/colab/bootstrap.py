"""Colab/local setup helpers (plan §1 of the notebook). Pure functions; the notebook only calls them."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


def pipeline_root(pipeline_id: str, mode: str, drive_root: str | None = None) -> Path:
    """Results folder; smoke runs go to `<id>_smoke` so they never mix with full runs."""
    base = Path(drive_root or "/content/drive/MyDrive/keycheck/pipeline")
    return base / (pipeline_id if mode == "full" else f"{pipeline_id}_smoke")


def in_colab() -> bool:
    return "google.colab" in sys.modules or os.path.exists("/content")


def mount_drive() -> None:
    if in_colab():
        from google.colab import drive  # type: ignore
        drive.mount("/content/drive")


def _run(cmd: list[str], cwd: str | None = None) -> str:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False).stdout.strip()
    except FileNotFoundError:
        return ""


def write_run_info(out_dir: str | Path, *, repo_dir: str | Path, seed: int, mode: str, extra: dict | None = None) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    info = {
        "time": time.strftime("%FT%T"),
        "commit": _run(["git", "rev-parse", "HEAD"], str(repo_dir)),
        "dirty": bool(_run(["git", "status", "--porcelain", "--untracked-files=no"], str(repo_dir))),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "seed": seed,
        "mode": mode,
        "nvidia_smi": _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"]),
        "pip_freeze": _run([sys.executable, "-m", "pip", "freeze"]).splitlines(),
        **(extra or {}),
    }
    (out_dir / "run_info.json").write_text(json.dumps(info, indent=1))
    return info


def seed_everything(seed: int) -> None:
    import random
    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def free_memory() -> None:
    import gc
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def env_check() -> dict:
    """Plan step 1: GPU visibility and whether Torch, Ultralytics and Paddle import together in one process."""
    rep: dict = {"python": platform.python_version(), "nvidia_smi": _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])}
    for mod in ("numpy", "cv2", "scipy", "yaml", "torch", "torchvision", "ultralytics", "paddle", "paddleocr"):
        try:
            m = __import__(mod)
            rep[mod] = getattr(m, "__version__", "ok")
        except Exception as e:                                # report, do not raise
            rep[mod] = f"IMPORT FAILED: {type(e).__name__}: {str(e)[:100]}"
    try:
        import torch
        rep["torch_cuda"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            rep["torch_gpu"] = torch.cuda.get_device_name(0)
    except Exception:
        pass
    try:
        import paddle
        rep["paddle_cuda"] = bool(paddle.device.is_compiled_with_cuda())
    except Exception:
        pass
    rep["verdict"] = ("OCR ต้องแยก Subprocess" if any(str(v).startswith("IMPORT FAILED") for k, v in rep.items() if k in ("torch", "ultralytics", "paddle", "paddleocr"))
                      else "Torch + Ultralytics + Paddle import ใน Env เดียวได้")
    return rep
