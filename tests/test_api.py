import pytest

from amfinder import web


@pytest.fixture()
def client():
    web.app.config.update(TESTING=True)
    web._RATE.clear()
    return web.app.test_client()


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True and "version" in body
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["X-Content-Type-Options"] == "nosniff"


def test_list_requires_query(client):
    r = client.post("/api/list", json={"platform": "youtube", "mode": "search", "query": ""})
    assert r.status_code == 422
    assert "Isi dulu" in r.get_json()["error"]


def test_list_rejects_bad_platform(client):
    r = client.post("/api/list", json={"platform": "facebook", "query": "x"})
    assert r.status_code == 422


def test_scan_validates_items(client):
    r = client.post(
        "/api/scan", json={"items": [{"platform": "youtube", "id": "../../etc/passwd"}, {"platform": "x", "id": "1"}]}
    )
    assert r.status_code == 400


def test_check_rejects_non_alight(client):
    r = client.post("/api/check", json={"url": "http://169.254.169.254/latest"})
    assert r.status_code == 400


def test_media_id_validation(client):
    assert client.get("/api/media/tiktok/abc").status_code == 400
    assert client.get("/api/stream/tiktok/12;rm").status_code in (400, 404)
    assert client.get("/api/stream/youtube/bad").status_code == 400


def test_qr_svg(client):
    r = client.get("/api/qr?d=https://alight.link/fHYPBiUvmEkV3kHk9")
    assert r.status_code == 200 and r.mimetype == "image/svg+xml"
    assert b"<svg" in r.data


def test_csv_formula_injection_escaped(client):
    rows = [
        {
            "platform": "youtube",
            "url": "https://youtu.be/x",
            "title": '=HYPERLINK("evil")',
            "author": "+cmd",
            "links": [{"type": "am", "url": "https://alight.link/x", "source": "deskripsi", "info": {"name": "@SUM(1)"}}],
        }
    ]
    r = client.post("/api/export.csv", json={"results": rows})
    text = r.data.decode("utf-8-sig")
    assert "'=HYPERLINK" in text and "'+cmd" in text and "'@SUM" in text


def test_rate_limit(client):
    for _ in range(20):
        client.post("/api/list", json={"platform": "youtube", "query": ""})
    r = client.post("/api/list", json={"platform": "youtube", "query": ""})
    assert r.status_code == 429
