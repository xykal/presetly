from amfinder.links import LinkBag, canon_file_url, extract_links, file_kind, host_matches, strip_truncated


def urls(text):
    return [(link["type"], link["url"]) for link in extract_links(text)]


def test_alight_short_and_share():
    got = urls(
        "PRESET https://alight.link/zB97ApWeDtVmEg7B #fyp\n"
        "5MB https://alightcreative.com/am/share/u/GYvgzxaojURMkwd2y70Q0rStl0E2/p/BwZphAJZiX-9a29db0869571c82"
    )
    assert ("am", "https://alight.link/zB97ApWeDtVmEg7B") in got
    assert ("am", "https://alightcreative.com/am/share/u/GYvgzxaojURMkwd2y70Q0rStl0E2/p/BwZphAJZiX-9a29db0869571c82") in got


def test_fancy_unicode_and_zero_width():
    assert urls(
        "\U0001d5ee\U0001d5f9\U0001d5f6\U0001d5f4\U0001d5f5\U0001d601.\U0001d5f9\U0001d5f6\U0001d5fb\U0001d5f8/HelloWorld12345678"
    ) == [("am", "https://alight.link/HelloWorld12345678")]
    assert urls("alight\u200b.link/fHYPBiUvmEkV3kHk9") == [("am", "https://alight.link/fHYPBiUvmEkV3kHk9")]


def test_non_latin_suffix_not_glued():
    got = urls(
        "https://drive.google.com/file/d/177TpW62maTmkWxyEBpFV4e_m89MW-_qw/view?usp=drivesdk\u1019\u1030\u101b\u1004\u103a\u1038"
    )
    assert got == [("xml", "https://drive.google.com/file/d/177TpW62maTmkWxyEBpFV4e_m89MW-_qw/view")]


def test_drive_canonical_dedupe():
    a = canon_file_url("https://drive.google.com/file/d/1abcdefghijklmnopqrs/view?usp=sharing")
    b = canon_file_url("https://drive.google.com/open?id=1abcdefghijklmnopqrs")
    assert a == b == "https://drive.google.com/file/d/1abcdefghijklmnopqrs/view"


def test_lookalike_hosts_rejected():
    assert urls("https://drive.google.com.evil.com/file/x") == [("other", "https://drive.google.com.evil.com/file/x")]
    assert host_matches("docs.google.com", ("google.com",))
    assert not host_matches("google.com.evil.com", ("google.com",))


def test_truncated_youtube_urls_stripped():
    text = "XML https://drive.google.com/file/d/10nhG... full https://alight.link/628yz4smw1A46R5Z9"
    assert urls(strip_truncated(text)) == [("am", "https://alight.link/628yz4smw1A46R5Z9")]


def test_file_kind():
    assert file_kind("https://files.catbox.moe/vzdm69.mp3") == "sound"
    assert file_kind("https://drive.google.com/drive/folders/1tcVMXRnJkd3g") == "folder"
    assert file_kind("https://drive.google.com/file/d/x/view", "Preset 12.xml") == "xml"


def test_linkbag_prefers_trusted_source():
    bag = LinkBag()
    bag.add_text("https://alight.link/fHYPBiUvmEkV3kHk9", "komen", "random")
    bag.add_text("https://alight.link/fHYPBiUvmEkV3kHk9", "balasan creator", "creator")
    (entry,) = bag.list()
    assert entry["source"] == "balasan creator" and entry["count"] == 2


def test_social_links_ignored():
    assert urls("ig https://instagram.com/foo yt https://youtu.be/abc tele https://t.me/abc") == [("other", "https://t.me/abc")]
