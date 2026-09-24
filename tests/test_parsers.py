import json

import pytest

from presetly.services.resolver import parse_share_page
from presetly.services.scanner import classify, yt_playlist_url
from presetly.sources import tiktok, youtube
from presetly.util import SourceError

SHARE_HTML = """
<meta property="og:title" content="Kyoka_PRESET" />
<meta property="og:image" content="https://firebasestorage.googleapis.com/x/thumb-small.jpg" />
<meta property="og:description" content="This Alight Motion package contains 2 projects, total 12.1 MB." />
<ul id="project-list"><li>Part 1</li><li>Part 2</li></ul>
<!-- amVersionCode=1002290 amVersionString=5.0.256.1002290 -->
"""


def test_parse_share_page():
    info = parse_share_page(SHARE_HTML)
    assert info["name"] == "Kyoka_PRESET"
    assert info["projects"] == 2
    assert info["size_mb"] == 12.1 and info["free_ok"] is False
    assert info["project_names"] == ["Part 1", "Part 2"]
    assert info["am_version"] == "5.0.256.1002290"


@pytest.mark.parametrize("size,unit,mb", [("685.9", "KB", 0.67), ("2.5", "KB", 0.002), ("1.2", "GB", 1228.8)])
def test_parse_share_units(size, unit, mb):
    html = SHARE_HTML.replace("total 12.1 MB", f"total {size} {unit}")
    assert parse_share_page(html)["size_mb"] == pytest.approx(mb, abs=0.01)


@pytest.mark.parametrize(
    "url,kind",
    [
        ("https://alight.link/fHYPBiUvmEkV3kHk9", "am"),
        ("vt.tiktok.com/ZSQ9KCg3K/", "tt_video"),
        ("https://www.tiktok.com/@a.b/video/7650863833069800725", "tt_video"),
        ("https://www.tiktok.com/tag/presetam", "tt_tag"),
        ("https://www.tiktok.com/@dan_newbie", "tt_profile"),
        ("https://youtu.be/oocjpCx6j84", "yt_video"),
        ("https://m.youtube.com/shorts/abcdefghijk", "yt_video"),
        ("https://www.youtube.com/playlist?list=PL0BnZXxgPPmYqZ0uJgTcoSfSlmLPTu33X", "yt_playlist"),
        ("https://www.youtube.com/@stwgguk", "yt_channel"),
        # SSRF / lookalike
        ("https://evil.com/?youtube.com/playlist?list=PLxxxxxxxxxx", None),
        ("https://youtube.com.evil.com/@x", None),
        ("http://169.254.169.254/latest/meta-data", None),
        ("javascript:alert(1)", None),
    ],
)
def test_classify(url, kind):
    assert classify(url) == kind


def test_playlist_url_rebuilt_from_id_only():
    assert (
        yt_playlist_url("https://www.youtube.com/watch?v=x&list=PL0BnZXxgPPmYqZ0uJgTc")
        == "https://www.youtube.com/playlist?list=PL0BnZXxgPPmYqZ0uJgTc"
    )
    assert yt_playlist_url("https://www.youtube.com/playlist?list=../../x") is None


def test_channel_base_rejects_foreign_hosts():
    assert youtube.channel_base("@stwgguk") == "https://www.youtube.com/@stwgguk"
    assert youtube.channel_base("https://www.youtube.com/@stwgguk/shorts") == "https://www.youtube.com/@stwgguk"
    with pytest.raises(SourceError):
        youtube.channel_base("https://evil.com/youtube.com/@x")


def test_youtube_date_parsing():
    assert youtube.parse_date("4 Mar 2026") == 1772582400
    assert youtube.parse_date("Tayang perdana 12 Agu 2025") == 1754956800
    assert youtube.parse_date("") is None


def test_youtube_watch_next_parser():
    j = {
        "contents": {
            "twoColumnWatchNextResults": {
                "results": {
                    "results": {
                        "contents": [
                            {
                                "videoPrimaryInfoRenderer": {
                                    "title": {"runs": [{"text": "PRESET AM"}]},
                                    "viewCount": {"videoViewCountRenderer": {"viewCount": {"simpleText": "5.734 x ditonton"}}},
                                    "dateText": {"simpleText": "4 Mar 2026"},
                                }
                            },
                            {
                                "videoSecondaryInfoRenderer": {
                                    "attributedDescription": {
                                        "content": "preset https://alight.link/628yz4...",
                                        "commandRuns": [
                                            {
                                                "onTap": {
                                                    "innertubeCommand": {
                                                        "urlEndpoint": {
                                                            "url": "https://www.youtube.com/redirect?q=https%3A%2F%2Falight.link%2F628yz4smw1A46R5Z9&v=x"
                                                        }
                                                    }
                                                }
                                            }
                                        ],
                                    },
                                    "owner": {
                                        "videoOwnerRenderer": {
                                            "title": {"runs": [{"text": "Jarfvy"}]},
                                            "navigationEndpoint": {"browseEndpoint": {"canonicalBaseUrl": "/@jarfvy"}},
                                        }
                                    },
                                }
                            },
                        ]
                    }
                }
            }
        }
    }
    d = youtube.parse_watch_next(j)
    assert d["title"] == "PRESET AM" and d["views"] == 5734 and d["author"] == "Jarfvy"
    assert d["desc_urls"] == ["https://alight.link/628yz4smw1A46R5Z9"]
    assert d["author_url"] == "https://www.youtube.com/@jarfvy"


def test_youtube_comments_parser():
    j = {
        "onResponseReceivedEndpoints": [
            {
                "reloadContinuationItemsCommand": {
                    "continuationItems": [
                        {
                            "commentThreadRenderer": {
                                "commentViewModel": {"commentViewModel": {"commentKey": "k1", "pinnedText": "Pinned"}}
                            }
                        },
                        {"commentThreadRenderer": {"commentViewModel": {"commentViewModel": {"commentKey": "k2"}}}},
                    ]
                }
            }
        ],
        "frameworkUpdates": {
            "entityBatchUpdate": {
                "mutations": [
                    {
                        "entityKey": "k1",
                        "payload": {
                            "commentEntityPayload": {
                                "properties": {"content": {"content": "link: alight.link/AbCdEfGhIjKlMnOpQ"}},
                                "author": {"displayName": "@creator", "isCreator": True},
                            }
                        },
                    },
                    {
                        "entityKey": "k2",
                        "payload": {
                            "commentEntityPayload": {
                                "properties": {"content": {"content": "keren"}},
                                "author": {"displayName": "@fan", "isCreator": False},
                            }
                        },
                    },
                ]
            }
        },
    }
    comments, nxt = youtube.parse_comments(j)
    assert nxt is None
    assert comments[0]["pinned"] and comments[0]["creator"]
    assert not comments[1]["pinned"] and not comments[1]["creator"]


def test_tiktok_embed_list_parser():
    state = {
        "source": {
            "data": {
                "/embed/@dan_newbie": {
                    "userInfo": {
                        "uniqueId": "dan_newbie",
                        "nickname": "Dan",
                        "signature": "cek bio\nhttps://alight.link/fHYPBiUvmEkV3kHk9",
                        "followerCount": 32200,
                        "heartCount": 924000,
                    },
                    "videoList": [
                        {
                            "id": "7688236713143012629",
                            "desc": "Silahkan pakai preset",
                            "authorUniqueId": "dan_newbie",
                            "playCount": 221000,
                            "coverUrl": "https://p16.tiktokcdn-us.com/c.jpg",
                            "playAddr": "https://v45.tiktokcdn-us.com/v.mp4",
                            "width": 1080,
                            "height": 1920,
                        },
                        {"id": "7688189845969063176", "privateItem": True},
                    ],
                }
            }
        }
    }
    prof, recs = tiktok.parse_embed_list(state, "/embed/@")
    assert prof["handle"] == "dan_newbie" and prof["followers"] == 32200
    assert len(recs) == 1
    r = recs[0]
    assert r["url"] == "https://www.tiktok.com/@dan_newbie/video/7688236713143012629"
    assert r["play"].endswith("v.mp4") and r["vertical"] is True and r["views"] == 221000
    assert r["ts"] == 7688236713143012629 >> 32


def test_tiktok_embed_video_parser():
    state = json.loads(
        json.dumps(
            {
                "source": {
                    "data": {
                        "/embed/v2/7650863833069800725": {
                            "videoData": {
                                "itemInfos": {
                                    "id": "7650863833069800725",
                                    "text": "magnolia",
                                    "playCount": 30700,
                                    "createTime": "1781355556",
                                    "covers": ["https://p19.tiktokcdn-us.com/c.jpg"],
                                    "video": {
                                        "urls": ["https://v45.tiktokcdn-us.com/v.mp4"],
                                        "videoMeta": {"width": 576, "height": 1024, "duration": 29},
                                    },
                                },
                                "authorInfos": {"uniqueId": "zin.ru4", "nickName": "Kyoka."},
                            }
                        }
                    }
                }
            }
        )
    )
    r = tiktok.parse_embed_video(state)
    assert r["author_handle"] == "zin.ru4" and r["duration"] == 29 and r["ts"] == 1781355556
    assert r["play"] == "https://v45.tiktokcdn-us.com/v.mp4"


def test_parse_user_and_tag():
    assert tiktok.parse_user("https://www.tiktok.com/@dan_newbie?lang=id") == "dan_newbie"
    assert tiktok.parse_tag("#preset am!!") == "presetam"
    assert tiktok.parse_tag("https://www.tiktok.com/tag/presetalightmotion?x=1") == "presetalightmotion"


def test_instagram_parse_url():
    from presetly.sources import instagram as ig

    assert ig.parse_url("https://www.instagram.com/reel/Ch74NvrD2UV/") == ("video", "Ch74NvrD2UV", None)
    assert ig.parse_url("https://instagram.com/dan.preset/reels/AbC123-xYz_/") == ("video", "AbC123-xYz_", "dan.preset")
    assert ig.parse_url("https://www.instagram.com/some.user_/p/AbC123-xYz/") == ("video", "AbC123-xYz", "some.user_")
    assert ig.parse_url("https://www.instagram.com/dan.preset/") == ("user", "dan.preset", None)
    assert ig.parse_url("https://evil.com/?instagram.com/reel/XXXXXXX/") == (None, None, None)
    assert ig.parse_url("https://www.instagram.com.evil.com/reel/XXXXXXX/") == (None, None, None)


def test_instagram_short_to_media_id():
    from presetly.sources.instagram import short_to_media_id

    assert short_to_media_id("Ch74NvrD2UV") == 2917172418798642453


def test_instagram_rec_from_node():
    from presetly.sources.instagram import _rec_from_node

    node = {
        "shortcode": "AbC123-xYz_",
        "is_video": True,
        "video_url": "https://scontent.cdninstagram.com/v/x.mp4",
        "video_view_count": 1234,
        "video_duration": 27.4,
        "like_count": 99,
        "taken_at_timestamp": 1700000000,
        "thumbnail_src": "https://scontent.cdninstagram.com/t.jpg",
        "dimensions": {"height": 1920, "width": 1080},
        "owner": {"username": "kreator"},
        "edge_media_to_caption": {"edges": [{"node": {"text": "preset gratis https://alight.link/abcd1234"}}]},
    }
    rec = _rec_from_node(node)
    assert rec["platform"] == "instagram" and rec["id"] == "AbC123-xYz_"
    assert rec["play"].endswith(".mp4") and rec["views"] == 1234
    assert rec["duration"] == 27 and rec["vertical"] is True
    assert "alight.link/abcd1234" in rec["caption"]

    scan_out = __import__("presetly.sources.instagram", fromlist=["scan"]).scan(dict(rec))
    assert any(lk["type"] == "am" for lk in scan_out["links"])


def test_classify_instagram():
    assert classify("https://www.instagram.com/reel/AbC123-xYz/") == "ig_video"
    assert classify("https://www.instagram.com/dan.preset/") == "ig_profile"
    assert classify("https://www.instagram.com/explore/tags/x/") is None


def test_tiktok_clean_play_picks_no_watermark():
    from presetly.sources.tiktok import clean_play

    wm = "https://v16.tiktokcdn.com/video/wm_token/abc.mp4"
    clean = "https://v16.tiktokcdn.com/video/tos/abc.mp4"
    assert clean_play([wm, clean]) == clean
    assert clean_play([clean, wm]) == clean
    assert clean_play(wm) == wm  # cuma varian wm -> tetap dipake (daripada nihil)
    assert clean_play([]) is None
    assert clean_play(None) is None
