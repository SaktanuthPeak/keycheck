import asyncio
from datetime import timedelta

from apiapp.core.ids import utcnow
from apiapp.worker.retention import RetentionService

from .fakes import FakeInspector


def err(r) -> str:
    return r.json()["error"]["code"]


async def test_image_then_metadata_retention_leaves_no_orphans(env):
    c = env.client()
    up = await env.upload(c)
    iid = (await env.submit(c, up["image_id"])).json()["inspection_id"]
    await env.wait(c, iid)
    retention = RetentionService(env.container)

    rep = await retention.run_once(utcnow() + timedelta(hours=env.settings.IMAGE_RETENTION_HOURS, minutes=1))
    assert rep.images_expired == 1 and rep.inspections_deleted == 0
    assert env.files() == []
    res = (await c.get(f"/api/v1/inspections/{iid}")).json()
    assert res["status"] == "completed" and res["image_expired"] is True and len(res["slots"]) == 26
    r = await c.get(up["image_url"])
    assert (r.status_code, err(r)) == (410, "IMAGE_EXPIRED")
    r = await env.submit(c, up["image_id"])
    assert (r.status_code, err(r)) == (410, "IMAGE_EXPIRED")
    assert (await env.container.uploads.get(up["image_id"])).reference_count == 1

    rep = await retention.run_once(utcnow() + timedelta(hours=env.settings.METADATA_RETENTION_HOURS, minutes=1))
    assert rep.inspections_deleted == 1
    assert (await c.get(f"/api/v1/inspections/{iid}")).status_code == 404
    assert await env.container.uploads.get(up["image_id"]) is None
    assert env.files() == []


async def test_unreferenced_upload_expires_completely(env):
    c = env.client()
    up = await env.upload(c)
    rep = await RetentionService(env.container).run_once(utcnow() + timedelta(hours=25))
    assert rep.images_expired == 1 and rep.uploads_deleted == 1
    assert env.files() == [] and await env.container.uploads.get(up["image_id"]) is None
    assert (await c.get(up["image_url"])).status_code == 404


async def test_active_job_keeps_its_image(make_env):
    fake = FakeInspector()
    gate = fake.block()
    async with make_env(fake=fake) as env:
        c = env.client()
        up = await env.upload(c)
        iid = (await env.submit(c, up["image_id"])).json()["inspection_id"]
        await env.wait(c, iid, until=("processing",))
        later = utcnow() + timedelta(hours=25)
        rep = await RetentionService(env.container).run_once(later)
        assert rep.images_expired == 0 and env.files() == [f"{up['image_id']}.jpg"]
        gate.set()
        assert (await env.wait(c, iid))["status"] == "completed"
        rep = await RetentionService(env.container).run_once(later)
        assert rep.images_expired == 1 and env.files() == []


async def test_orphan_files_swept(make_env):
    async with make_env(ORPHAN_GRACE_SECONDS=0, start_worker=False) as env:  # no concurrent startup sweep
        c = env.client()
        up = await env.upload(c)
        (env.images_dir / "img_orphan00000000000000.jpg").write_bytes(b"x")
        (env.images_dir / ".tmp_abandoned").write_bytes(b"x")
        rep = await RetentionService(env.container).run_once()
        assert rep.orphans_deleted == 2
        assert env.files() == [f"{up['image_id']}.jpg"]


async def test_retention_runs_periodically_in_worker(make_env):
    async with make_env(IMAGE_RETENTION_HOURS=1 / 3600, RETENTION_INTERVAL_SECONDS=0.2) as env:
        c = env.client()
        up = await env.upload(c)
        assert env.files()
        for _ in range(100):
            if not env.files():
                break
            await asyncio.sleep(0.1)
        assert env.files() == []
        assert (await c.get(up["image_url"])).status_code in (404, 410)
