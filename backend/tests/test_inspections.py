import asyncio
import uuid

from .fakes import GOOD_POINTS, FakeInspector, image_bytes


def err(r) -> str:
    return r.json()["error"]["code"]


async def test_full_flow_upload_inspection_worker_result(make_env):
    fake = FakeInspector("swap")
    async with make_env(fake=fake) as env:
        c = env.client()
        up = await env.upload(c, image_bytes("JPEG", (800, 400)))
        r = await env.submit(c, up["image_id"])
        assert r.status_code == 202
        acc = r.json()
        assert acc["status"] == "queued" and acc["inspection_id"].startswith("ins_")
        assert acc["status_url"] == f"/api/v1/inspections/{acc['inspection_id']}"

        res = await env.wait(c, acc["inspection_id"])
        assert res["status"] == "completed" and res["error"] is None
        assert res["model_bundle_id"] == "fake_bundle_v0" and res["layout_version"] == 1
        assert res["coordinate_system"] == "original_oriented_normalized"
        assert (res["image_width"], res["image_height"], res["image_expired"]) == (800, 400, False)
        assert res["reference_points_normalized"] == GOOD_POINTS
        s = res["summary"]
        assert s["correct"] + s["incorrect"] + s["uncertain"] == s["total_slots"] == len(res["slots"]) == 26
        assert s["incorrect"] == 2
        assert res["suggestions"] == [{"type": "swap_pair", "slots": ["r1c0", "r1c1"]}]
        assert res["warnings"] == ["layout_fit_not_checked"] and res["timings_ms"]["total"] == 7
        assert res["finished_at"] and res["stage"] is None
        slot = res["slots"][0]
        assert set(slot) >= {"slot_id", "row", "col", "expected_label", "observed_label", "status", "reason",
                             "reason_codes", "detector_score", "ocr_score", "assignment_distance", "polygon",
                             "polygon_source", "is_reference"}
        assert slot["detector_score"] is None
        # normalised points -> pixels on the stored oriented image
        (hw, pts), = fake.calls
        assert hw == (400, 800)
        assert pts[0] == [0.1 * 800, 0.2 * 400]

        r = await c.get("/api/v1/inspections")
        assert [i["inspection_id"] for i in r.json()["items"]] == [acc["inspection_id"]]


async def test_stage_is_reported_while_processing(make_env):
    fake = FakeInspector()
    gate = fake.block()
    async with make_env(fake=fake) as env:
        c = env.client()
        up = await env.upload(c)
        iid = (await env.submit(c, up["image_id"])).json()["inspection_id"]
        body = None
        for _ in range(200):
            body = (await c.get(f"/api/v1/inspections/{iid}")).json()
            if body["stage"] == "reading":
                break
            await asyncio.sleep(0.05)
        assert body["status"] == "processing" and body["stage"] == "reading" and body["slots"] == []
        r = await c.delete(f"/api/v1/inspections/{iid}")
        assert (r.status_code, err(r)) == (409, "INSPECTION_IN_PROGRESS")
        r = await c.delete(f"/api/v1/uploads/{up['image_id']}")
        assert (r.status_code, err(r)) == (409, "IMAGE_IN_USE")
        gate.set()
        assert (await env.wait(c, iid))["status"] == "completed"


async def test_invalid_corners_rejected_at_api(env):
    c = env.client()
    up = await env.upload(c)
    cases = [
        [[0.9, 0.2], [0.1, 0.2], [0.72, 0.8], [0.18, 0.8]],  # TL/TR swapped -> crossing
        [[0.1, 0.2], [0.9, 0.2], [0.72, 0.8]],  # 3 points
        [[0.1, 0.2], [1.2, 0.2], [0.72, 0.8], [0.18, 0.8]],  # outside 0..1
        [[0.1, 0.2, 0.3], [0.9, 0.2], [0.72, 0.8], [0.18, 0.8]],  # not a pair
        [[0.5, 0.5], [0.501, 0.5], [0.501, 0.501], [0.5, 0.501]],  # area too small
        [["a", 0.2], [0.9, 0.2], [0.72, 0.8], [0.18, 0.8]],  # not numbers
    ]
    for pts in cases:
        r = await env.submit(c, up["image_id"], points=pts)
        assert (r.status_code, err(r)) == (422, "INVALID_CORNERS"), pts
    assert (await env.container.uploads.get(up["image_id"])).reference_count == 0


async def test_worker_invalid_points_and_layout_mismatch(make_env):
    for mode, code in (("invalid", "INVALID_CORNERS"), ("reject", "LAYOUT_MISMATCH")):
        async with make_env(fake=FakeInspector(mode)) as env:
            c = env.client()
            up = await env.upload(c)
            iid = (await env.submit(c, up["image_id"])).json()["inspection_id"]
            res = await env.wait(c, iid)
            assert res["status"] == "rejected" and res["error"]["code"] == code
            assert res["error"]["retryable"] is True and res["error"]["message"]
            assert res["slots"] == [] and res["summary"] is None


async def test_layout_and_image_checks(env):
    c = env.client()
    up = await env.upload(c)
    r = await c.post("/api/v1/inspections", json={"image_id": up["image_id"], "layout_id": "qwertz_letters_eval_v1",
                                                  "reference_points_normalized": GOOD_POINTS})
    assert (r.status_code, err(r)) == (422, "LAYOUT_NOT_FOUND")  # internal_only layouts are never served
    r = await env.submit(c, "img_aaaaaaaaaaaaaaaaaaaa")
    assert (r.status_code, err(r)) == (404, "NOT_FOUND")


async def test_duplicate_submit_same_client_request_id_creates_one_job(env):
    c = env.client()
    up = await env.upload(c)
    crid = str(uuid.uuid4())
    r1 = await env.submit(c, up["image_id"], client_request_id=crid)
    r2 = await env.submit(c, up["image_id"], client_request_id=crid)
    assert r1.status_code == r2.status_code == 202
    assert r1.json()["inspection_id"] == r2.json()["inspection_id"]
    await env.wait(c, r1.json()["inspection_id"])
    r3 = await env.submit(c, up["image_id"], client_request_id=crid)  # after completion too
    assert r3.json()["inspection_id"] == r1.json()["inspection_id"]
    assert len((await c.get("/api/v1/inspections")).json()["items"]) == 1
    assert len(env.fake.calls) == 1
    assert (await env.container.uploads.get(up["image_id"])).reference_count == 1
    # the same key in another session is a different request
    other = env.client()
    up2 = await env.upload(other)
    r4 = await env.submit(other, up2["image_id"], client_request_id=crid)
    assert r4.json()["inspection_id"] != r1.json()["inspection_id"]


async def test_queue_full_per_session_and_global(make_env):
    fake = FakeInspector()
    gate = fake.block()
    async with make_env(fake=fake, QUEUE_CAPACITY=3, MAX_ACTIVE_JOBS_PER_SESSION=2) as env:
        a, b = env.client(), env.client()
        ua, ub = await env.upload(a), await env.upload(b)
        assert (await env.submit(a, ua["image_id"])).status_code == 202
        assert (await env.submit(a, ua["image_id"])).status_code == 202
        r = await env.submit(a, ua["image_id"])
        assert (r.status_code, err(r)) == (429, "QUEUE_FULL") and r.json()["error"]["retryable"] is True
        assert (await env.submit(b, ub["image_id"])).status_code == 202
        r = await env.submit(b, ub["image_id"])  # 3 active in total
        assert (r.status_code, err(r)) == (429, "QUEUE_FULL")
        assert (await env.container.uploads.get(ua["image_id"])).reference_count == 2
        gate.set()
        items = (await a.get("/api/v1/inspections")).json()["items"]
        for it in items:
            await env.wait(a, it["inspection_id"])
        assert (await env.submit(a, ua["image_id"])).status_code == 202


async def test_other_session_cannot_read_or_delete_result(env):
    a, b = env.client(), env.client()
    up = await env.upload(a)
    iid = (await env.submit(a, up["image_id"])).json()["inspection_id"]
    await env.wait(a, iid)
    for r in (await b.get(f"/api/v1/inspections/{iid}"), await b.delete(f"/api/v1/inspections/{iid}")):
        assert (r.status_code, err(r)) == (404, "NOT_FOUND")
    r = await env.submit(b, up["image_id"])  # cannot inspect someone else's image either
    assert (r.status_code, err(r)) == (404, "NOT_FOUND")
    assert (await b.get("/api/v1/inspections")).json() == {"items": [], "next_cursor": None}
    assert (await a.get(f"/api/v1/inspections/{iid}")).status_code == 200


async def test_delete_inspection_removes_unreferenced_image(env):
    c = env.client()
    up = await env.upload(c)
    i1 = (await env.submit(c, up["image_id"])).json()["inspection_id"]
    await env.wait(c, i1)
    i2 = (await env.submit(c, up["image_id"])).json()["inspection_id"]
    await env.wait(c, i2)
    assert (await c.delete(f"/api/v1/inspections/{i1}")).status_code == 204
    assert env.files() == [f"{up['image_id']}.jpg"]  # still referenced by i2
    assert (await c.get(f"/api/v1/inspections/{i1}")).status_code == 404
    assert (await c.delete(f"/api/v1/inspections/{i2}")).status_code == 204
    assert env.files() == []
    assert await env.container.uploads.get(up["image_id"]) is None
    assert (await c.get(up["image_url"])).status_code == 404


async def test_list_pagination(make_env):
    async with make_env(MAX_ACTIVE_JOBS_PER_SESSION=10, QUEUE_CAPACITY=10) as env:
        c = env.client()
        up = await env.upload(c)
        ids = []
        for _ in range(5):
            iid = (await env.submit(c, up["image_id"])).json()["inspection_id"]
            await env.wait(c, iid)
            ids.append(iid)
        seen, cursor = [], None
        while True:
            params = {"limit": 2} | ({"cursor": cursor} if cursor else {})
            page = (await c.get("/api/v1/inspections", params=params)).json()
            seen += [i["inspection_id"] for i in page["items"]]
            assert all(i["status"] == "completed" and i["summary"]["total_slots"] == 26 for i in page["items"])
            cursor = page["next_cursor"]
            if not cursor:
                break
        assert seen == list(reversed(ids))
        r = await c.get("/api/v1/inspections", params={"cursor": "not-a-cursor"})
        assert (r.status_code, err(r)) == (422, "VALIDATION_ERROR")


async def test_origin_check_on_state_changing_requests(make_env):
    async with make_env(ALLOWED_ORIGINS=["https://keycheck.example"]) as env:
        c = env.client()
        files = {"image": ("a.jpg", image_bytes(), "image/jpeg")}
        r = await c.post("/api/v1/uploads", files=files, headers={"Origin": "https://evil.example"})
        assert (r.status_code, err(r)) == (403, "ORIGIN_FORBIDDEN")
        r = await c.post("/api/v1/uploads", files=files, headers={"Origin": "null"})
        assert (r.status_code, err(r)) == (403, "ORIGIN_FORBIDDEN")
        assert env.files() == []
        assert (await c.post("/api/v1/uploads", files=files, headers={"Origin": "http://test"})).status_code == 201
        r = await c.post("/api/v1/uploads", files=files, headers={"Origin": "https://keycheck.example"})
        assert r.status_code == 201
        up = await env.upload(c)  # no Origin header (non-browser client)
        r = await c.delete(f"/api/v1/uploads/{up['image_id']}", headers={"Origin": "https://evil.example"})
        assert (r.status_code, err(r)) == (403, "ORIGIN_FORBIDDEN")
        assert (await c.get(up["image_url"], headers={"Origin": "https://evil.example"})).status_code == 200
