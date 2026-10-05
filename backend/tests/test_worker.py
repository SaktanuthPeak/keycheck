import asyncio
import os
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

from apiapp.core.errors import ErrorCode
from apiapp.core.ids import utcnow
from apiapp.worker.runner import terminal_fields

from .conftest import MONGO_URI, mongo_available
from .fakes import FakeInspector


async def _wait_health_model(env, want: str) -> dict:
    for _ in range(200):
        body = (await env.client().get("/api/v1/health")).json()
        if body["model"] == want:
            return body
        await asyncio.sleep(0.05)
    raise AssertionError(body)


async def test_model_load_failure_fails_jobs_not_stuck(make_env):
    def broken(layout_id):
        raise FileNotFoundError("bundle.json")

    async with make_env(factory=broken) as env:
        health = await _wait_health_model(env, "error")
        assert health["status"] == "degraded"
        c = env.client()
        up = await env.upload(c)
        iid = (await env.submit(c, up["image_id"])).json()["inspection_id"]
        res = await env.wait(c, iid)
        assert res["status"] == "failed" and res["error"]["code"] == "MODEL_UNAVAILABLE"
        assert res["slots"] == [] and res["summary"] is None


async def test_inspector_exception_is_processing_failed(make_env):
    async with make_env(fake=FakeInspector("error")) as env:
        c = env.client()
        up = await env.upload(c)
        res = await env.wait(c, (await env.submit(c, up["image_id"])).json()["inspection_id"])
        assert res["status"] == "failed" and res["error"] == {
            "code": "PROCESSING_FAILED", "message": res["error"]["message"], "retryable": True}
        assert "boom" not in str(res) and "Traceback" not in str(res)


async def test_crashed_worker_lease_expires_then_job_is_requeued_and_completed(make_env):
    async with make_env(start_worker=False, WORKER_LEASE_SECONDS=1, WORKER_MAX_RETRIES=1) as env:
        c = env.client()
        up = await env.upload(c)
        iid = (await env.submit(c, up["image_id"])).json()["inspection_id"]
        # a worker claims the job and dies without heartbeats
        job = await env.container.inspections.claim("dead-worker", utcnow(), 1.0)
        assert job is not None and job.inspection_id == iid
        assert (await c.get(f"/api/v1/inspections/{iid}")).json()["status"] == "processing"

        env.start_worker(worker_id="live-worker")
        res = await env.wait(c, iid, timeout=20)
        assert res["status"] == "completed"
        rec = await env.container.inspections.get(iid)
        assert rec.worker_lease.worker_id == "live-worker" and rec.worker_lease.retry_count == 1
        # the dead worker can no longer write its (stale) result
        assert not await env.container.inspections.finish(iid, "dead-worker", terminal_fields("failed"))


async def test_crashed_worker_retries_exhausted_job_failed(make_env):
    async with make_env(start_worker=False, WORKER_LEASE_SECONDS=1, WORKER_MAX_RETRIES=0) as env:
        c = env.client()
        up = await env.upload(c)
        iid = (await env.submit(c, up["image_id"])).json()["inspection_id"]
        assert await env.container.inspections.claim("dead-worker", utcnow(), 1.0) is not None
        env.start_worker()
        res = await env.wait(c, iid, timeout=20)
        assert res["status"] == "failed" and res["error"]["code"] == "PROCESSING_FAILED"
        assert len(env.fake.calls) == 0


async def test_lease_recovery_is_bounded(make_env):
    async with make_env(start_worker=False, WORKER_LEASE_SECONDS=30, WORKER_MAX_RETRIES=1) as env:
        repo = env.container.inspections
        c = env.client()
        up = await env.upload(c)
        iid = (await env.submit(c, up["image_id"])).json()["inspection_id"]
        failed = terminal_fields("failed", ErrorCode.PROCESSING_FAILED)
        t0 = utcnow()
        assert (await repo.claim("w1", t0, 1.0)).inspection_id == iid
        assert await repo.recover_expired_leases(t0 + timedelta(seconds=10), 30, 1, failed) == ([], [])
        assert await repo.heartbeat(iid, "w1", t0 + timedelta(seconds=20))
        assert await repo.recover_expired_leases(t0 + timedelta(seconds=60), 30, 1, failed) == ([iid], [])
        assert not await repo.heartbeat(iid, "w1", t0 + timedelta(seconds=61))
        t1 = utcnow()
        assert (await repo.claim("w2", t1, 1.0)).worker_lease.retry_count == 1
        assert await repo.recover_expired_leases(t1 + timedelta(seconds=60), 30, 1, failed) == ([], [iid])
        res = (await c.get(f"/api/v1/inspections/{iid}")).json()
        assert res["status"] == "failed" and res["error"]["code"] == "PROCESSING_FAILED"
        # failed jobs can be deleted and release their image
        assert (await c.delete(f"/api/v1/inspections/{iid}")).status_code == 204
        assert env.files() == []


def test_mongo_mode_api_does_not_import_inference_stack():
    """In MongoDB mode the API process must not load ai.inference / paddle / the worker."""
    uri = MONGO_URI if mongo_available() else "mongodb://127.0.0.1:1/never"
    code = f"""
import asyncio, sys
from apiapp.core.config import Settings
from apiapp.run import create_app
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
s = Settings(_env_file=None, SESSION_SECRET="x" * 32, MONGODB_URI={uri!r})
app = create_app(s)
async def main():
    if {mongo_available()!r}:
        async with LifespanManager(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                assert (await c.get("/api/v1/health")).json()["database"] == "ok"
asyncio.run(main())
bad = sorted(m for m in sys.modules if m.split(".")[0] in ("paddle", "paddleocr", "paddlex", "torch")
             or m.startswith(("ai.inference", "apiapp.worker")))
print(bad)
sys.exit(1 if bad else 0)
"""
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": ""}
    r = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1], env=env,
                       capture_output=True, text=True, timeout=120, check=False)
    assert r.returncode == 0, r.stdout + r.stderr[-2000:]
