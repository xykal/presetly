import pytest

from presetly import web


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


def test_api_404_is_json(client):
    r = client.get("/api/gak-ada")
    assert r.status_code == 404
    assert r.is_json and "error" in r.get_json()


def test_api_unhandled_is_json(client, monkeypatch):
    def boom():
        raise RuntimeError("meledak")

    monkeypatch.setattr("presetly.web.feed.get_feed", boom)
    r = client.get("/api/feed")
    assert r.status_code == 500
    assert r.is_json and r.get_json()["error"]


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["Referrer-Policy"] == "no-referrer"


def test_push_endpoints_validation(client, monkeypatch):
    monkeypatch.setattr("presetly.push.D1_TOKEN", "")  # push nonaktif
    r = client.get("/api/push/config")
    assert r.status_code == 200 and r.get_json()["enabled"] is False
    r = client.post("/api/push/subscribe", json={"endpoint": "https://x", "keys": {}})
    assert r.status_code == 503

    monkeypatch.setattr("presetly.push.D1_TOKEN", "x")
    monkeypatch.setattr("presetly.push.VAPID_PRIV", "x")
    monkeypatch.setattr("presetly.push.VAPID_PUB", "x")
    r = client.post("/api/push/subscribe", json={"endpoint": "http://jelek", "keys": {"p256dh": "a", "auth": "b"}})
    assert r.status_code == 400
    r = client.post("/api/push/subscribe", json={"endpoint": "https://ok", "keys": {"p256dh": "a"}, "creators": "x"})
    assert r.status_code == 400
    r = client.post("/api/push/unsubscribe", json={})
    assert r.status_code == 400

    monkeypatch.setattr("presetly.push.PUSH_SECRET", "rahasia")
    assert client.post("/api/push/run").status_code == 403
    assert client.post("/api/push/run", headers={"X-Presetly-Secret": "salah"}).status_code == 403


def test_push_norm_creators():
    from presetly.push import _norm_creators

    got = _norm_creators(["@Dan_Newbie", "yt:@StwGguk", "ig:kreator.am", "tiktok:dan_newbie", "fb:x", "youtube:@StwGguk"])
    assert got == ["tiktok:dan_newbie", "youtube:@stwgguk", "instagram:kreator.am"]
