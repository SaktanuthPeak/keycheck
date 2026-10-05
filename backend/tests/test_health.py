from apiapp.core.session import COOKIE_NAME


async def test_health_reports_api_db_model(env):
    r = await env.client().get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"status", "api", "database", "model", "model_bundle_id"}
    assert body["api"] == "ok"
    assert body["database"] == ("memory" if env.mode == "memory" else "ok")
    # the worker publishes its status once the (fake) model is loaded
    for _ in range(100):
        body = (await env.client().get("/api/v1/health")).json()
        if body["model"] == "ready":
            break
        import asyncio

        await asyncio.sleep(0.05)
    assert body["model"] == "ready" and body["model_bundle_id"] == "fake_bundle_v0"
    assert body["status"] == "ok"
    assert "SESSION_SECRET" not in r.text and "mongodb://" not in r.text


async def test_layouts_public_only(env):
    r = await env.client().get("/api/v1/layouts")
    assert r.status_code == 200
    layouts = r.json()["layouts"]
    assert [lay["layout_id"] for lay in layouts] == ["qwerty_stagger_letters_v1"]
    lay = layouts[0]
    assert lay["version"] == 1 and len(lay["slots"]) == 26
    assert [(p["order"], p["slot_id"], p["expected_label"]) for p in lay["reference_points"]] == [
        ("TL", "r0c0", "Q"), ("TR", "r0c9", "P"), ("BR", "r2c6", "M"), ("BL", "r2c0", "Z")]
    assert set(lay["slots"][0]) == {"slot_id", "row", "col", "expected_label"}


async def test_session_cookie_issued_once_and_only_hash_stored(env):
    c = env.client()
    r = await c.get("/api/v1/health")
    sc = r.headers["set-cookie"]
    assert sc.startswith(f"{COOKIE_NAME}=")
    low = sc.lower()
    assert "httponly" in low and "samesite=lax" in low and "path=/" in low and "secure" not in low
    token = c.cookies[COOKIE_NAME]
    r2 = await c.get("/api/v1/health")
    assert "set-cookie" not in r2.headers  # existing session kept

    up = await env.upload(c)
    rec = await env.container.uploads.get(up["image_id"])
    assert rec.owner_session_hash != token and len(rec.owner_session_hash) == 64
    assert token not in rec.model_dump_json()


async def test_errors_use_contract_shape(env):
    c = env.client()
    r = await c.get("/api/v1/nope")
    assert r.status_code == 404
    assert r.json() == {"error": {"code": "NOT_FOUND", "message": r.json()["error"]["message"], "retryable": False}}
    r = await c.post("/api/v1/inspections", json={"layout_id": "x"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR"
