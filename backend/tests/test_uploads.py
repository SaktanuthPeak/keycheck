import io
import os

from PIL import ExifTags, Image

from .fakes import image_bytes


def noise_jpeg(size=(300, 300)) -> bytes:
    im = Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=95)
    return buf.getvalue()


def err(r) -> str:
    return r.json()["error"]["code"]


async def test_upload_jpeg_and_png(env):
    c = env.client()
    up = await env.upload(c)
    assert up["image_id"].startswith("img_") and (up["width"], up["height"]) == (400, 200)
    assert up["mime_type"] == "image/jpeg" and up["image_url"] == f"/api/v1/uploads/{up['image_id']}/image"
    assert up["created_at"].endswith("Z") and up["expires_at"] > up["created_at"]
    png = await env.upload(c, image_bytes("PNG", (64, 32)), name="x.png", ctype="image/png")
    assert png["mime_type"] == "image/png" and (png["width"], png["height"]) == (64, 32)
    assert sorted(env.files()) == sorted([f"{up['image_id']}.jpg", f"{png['image_id']}.png"])

    r = await c.get(up["image_url"])
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/jpeg"
    assert r.headers["cache-control"].startswith("private")
    assert Image.open(io.BytesIO(r.content)).size == (400, 200)


async def test_exif_rotated_upload_reports_oriented_size_and_strips_metadata(env):
    exif = Image.Exif()
    exif[ExifTags.Base.Orientation] = 6  # rotate 90 CW on display
    exif[ExifTags.Base.Make] = "TestCam"
    exif[ExifTags.IFD.GPSInfo] = {ExifTags.GPS.GPSLatitudeRef: "N", ExifTags.GPS.GPSLatitude: (7.0, 0.0, 0.0)}
    raw = image_bytes("JPEG", (400, 200), exif=exif)
    assert Image.open(io.BytesIO(raw)).getexif().get(ExifTags.Base.Orientation) == 6

    c = env.client()
    up = await env.upload(c, raw)
    assert (up["width"], up["height"]) == (200, 400)
    stored = (await c.get(up["image_url"])).content
    im = Image.open(io.BytesIO(stored))
    assert im.size == (200, 400)
    assert len(im.getexif()) == 0
    assert b"TestCam" not in stored and b"Exif\x00\x00" not in stored


async def test_too_large_bytes(make_env):
    async with make_env(MAX_UPLOAD_BYTES=20_000) as env:
        c = env.client()
        small_over = noise_jpeg((150, 150))  # above the limit, below limit + multipart slack: service check
        assert 20_000 < len(small_over) < 20_000 + 64 * 1024
        r = await c.post("/api/v1/uploads", files={"image": ("a.jpg", small_over, "image/jpeg")})
        assert (r.status_code, err(r)) == (413, "IMAGE_TOO_LARGE")
        big = noise_jpeg((400, 400))  # rejected from Content-Length by the body limit middleware
        assert len(big) > 20_000 + 64 * 1024
        r = await c.post("/api/v1/uploads", files={"image": ("a.jpg", big, "image/jpeg")})
        assert (r.status_code, err(r)) == (413, "IMAGE_TOO_LARGE")
        assert env.files() == []


async def test_too_many_pixels(make_env):
    async with make_env(MAX_IMAGE_PIXELS=10_000) as env:
        r = await env.client().post("/api/v1/uploads",
                                    files={"image": ("a.png", image_bytes("PNG", (200, 100)), "image/png")})
        assert (r.status_code, err(r)) == (413, "IMAGE_TOO_LARGE")
        assert env.files() == []


async def test_wrong_type_rejected_by_magic_bytes(env):
    c = env.client()
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, "GIF")
    heic = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic" + b"\x00" * 200
    for data, name, ctype in [
        (gif.getvalue(), "a.gif", "image/gif"),
        (heic, "IMG_0001.HEIC", "image/heic"),
        (b"just text pretending", "a.jpg", "image/jpeg"),  # client name / type are not trusted
        (b"", "empty.jpg", "image/jpeg"),
    ]:
        r = await c.post("/api/v1/uploads", files={"image": (name, data, ctype)})
        assert (r.status_code, err(r)) == (415, "UNSUPPORTED_IMAGE"), name
    assert env.files() == []


async def test_undecodable_rejected(env):
    c = env.client()
    good = noise_jpeg((120, 120))
    for data in [b"\xff\xd8\xff\xe0" + b"garbage" * 50, good[: len(good) // 2], b"\x89PNG\r\n\x1a\n" + b"\x00" * 64]:
        r = await c.post("/api/v1/uploads", files={"image": ("a.jpg", data, "image/jpeg")})
        assert (r.status_code, err(r)) == (422, "IMAGE_DECODE_FAILED")
    r = await c.post("/api/v1/uploads", files={"other": ("a.jpg", good, "image/jpeg")})
    assert (r.status_code, err(r)) == (422, "VALIDATION_ERROR")
    assert env.files() == []


async def test_other_session_cannot_read_or_delete_image(env):
    a, b = env.client(), env.client()
    up = await env.upload(a)
    r = await b.get(up["image_url"])
    assert (r.status_code, err(r)) == (404, "NOT_FOUND")
    r = await b.delete(f"/api/v1/uploads/{up['image_id']}")
    assert (r.status_code, err(r)) == (404, "NOT_FOUND")
    assert (await a.get(up["image_url"])).status_code == 200
    for bad in ["img_doesnotexist0000000", "..%2F..%2Fetc%2Fpasswd", "img_AAAAAAAAAAAAAAAAAAAA"]:
        assert (await a.get(f"/api/v1/uploads/{bad}/image")).status_code == 404


async def test_delete_upload(env):
    c = env.client()
    up = await env.upload(c)
    r = await c.delete(f"/api/v1/uploads/{up['image_id']}")
    assert r.status_code == 204
    assert env.files() == []
    assert (await c.get(up["image_url"])).status_code == 404
