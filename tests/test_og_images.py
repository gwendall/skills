import importlib.util
import struct
import sys
import unittest
import zlib
from email.message import Message
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_check_og():
    path = ROOT / "skills/engineering/og-images/scripts/check-og.py"
    spec = importlib.util.spec_from_file_location("check_og", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check_og = load_check_og()


def png(width, height):
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    chunk = struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr))
    return b"\x89PNG\r\n\x1a\n" + chunk


def jpeg(width, height):
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, height, width, 1) + b"\x01\x11\x00"
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"


def headers(**values):
    m = Message()
    for key, value in values.items():
        if isinstance(value, list):
            for v in value:
                m[key.replace("_", "-")] = v
        else:
            m[key.replace("_", "-")] = value
    return m


class ImageSizeTest(unittest.TestCase):
    def test_png(self):
        self.assertEqual(check_og.image_size(png(1200, 630)), (1200, 630, "png"))

    def test_jpeg_skips_app_segments(self):
        self.assertEqual(check_og.image_size(jpeg(1080, 1080)), (1080, 1080, "jpeg"))

    def test_gif(self):
        self.assertEqual(check_og.image_size(b"GIF89a" + struct.pack("<HH", 300, 157)), (300, 157, "gif"))

    def test_webp_vp8x(self):
        data = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"VP8X" + b"\x00" * 8 + (1199).to_bytes(3, "little") + (629).to_bytes(3, "little")
        self.assertEqual(check_og.image_size(data), (1200, 630, "webp"))

    def test_unknown(self):
        self.assertIsNone(check_og.image_size(b"<html>"))


class MetaTest(unittest.TestCase):
    def test_first_occurrence_wins_and_keys_are_lowercased(self):
        html = '<meta property="og:image" content="https://a/1.png"><meta property="OG:IMAGE" content="https://a/2.png"><meta name="twitter:card" content="summary_large_image">'
        meta = check_og.parse_meta(html)
        self.assertEqual(meta["og:image"], "https://a/1.png")
        self.assertEqual(meta["twitter:card"], "summary_large_image")

    def test_relative_image_is_an_error(self):
        findings = []
        check_og.check_page_meta("https://x.com/p", {"og:image": "/og.png"}, b"og:image", findings)
        self.assertTrue(any(level == "error" and "relative" in msg for level, msg in findings))

    def test_localhost_image_is_an_error(self):
        findings = []
        check_og.check_page_meta("https://x.com/p", {"og:image": "http://localhost:3000/og.png"}, b"og:image", findings)
        self.assertTrue(any(level == "error" and "local host" in msg for level, msg in findings))

    def test_tag_past_first_megabyte_is_an_error(self):
        findings = []
        html = b" " * (check_og.HTML_LIMIT + 10) + b"og:image"
        check_og.check_page_meta("https://x.com/p", {"og:image": "https://x.com/og.png"}, html, findings)
        self.assertTrue(any("first megabyte" in msg for _, msg in findings))

    def test_complete_tags_have_no_findings(self):
        meta = {"og:image": "https://x.com/og.png", "twitter:card": "summary_large_image", "og:title": "t",
                "og:url": "https://x.com/p", "og:image:alt": "a", "og:image:width": "1200", "og:image:height": "630"}
        findings = []
        check_og.check_page_meta("https://x.com/p", meta, b"og:image", findings)
        self.assertEqual(findings, [])


class CheckImageTest(unittest.TestCase):
    def run_check(self, body, status=200, ctype="image/png", cache=("public, max-age=60",), meta=None):
        hdrs = headers(Content_Type=ctype, Cache_Control=list(cache))
        with mock.patch.object(check_og, "fetch", return_value=(status, "https://x.com/og.png", hdrs, body)):
            findings = []
            info = check_og.check_image("https://x.com/og.png", "ua", meta or {}, findings)
        return info, findings

    def test_good_card(self):
        info, findings = self.run_check(png(1200, 630) + b"\x00" * 1000)
        self.assertEqual(info["size"], (1200, 630, "png"))
        self.assertEqual(findings, [])

    def test_over_whatsapp_limit_is_an_error(self):
        _, findings = self.run_check(png(1200, 630) + b"\x00" * 700_000)
        self.assertTrue(any(level == "error" and "600 KB" in msg for level, msg in findings))

    def test_between_targets_is_a_warning(self):
        _, findings = self.run_check(png(1200, 630) + b"\x00" * 400_000)
        self.assertEqual([level for level, _ in findings], ["warn"])

    def test_square_is_an_error(self):
        _, findings = self.run_check(png(1080, 1080))
        self.assertTrue(any("near square" in msg for _, msg in findings))

    def test_non_200_is_an_error(self):
        _, findings = self.run_check(b"denied", status=403, ctype="text/html")
        self.assertTrue(any(level == "error" and "403" in msg for level, msg in findings))

    def test_duplicate_cache_control_is_flagged(self):
        _, findings = self.run_check(png(1200, 630), cache=("public, max-age=60", "public, max-age=60"))
        self.assertTrue(any("Cache-Control" in msg for _, msg in findings))

    def test_declared_size_mismatch_is_flagged(self):
        _, findings = self.run_check(png(1200, 630), meta={"og:image:width": "800", "og:image:height": "418"})
        self.assertTrue(any("say 800x418" in msg for _, msg in findings))


if __name__ == "__main__":
    unittest.main()
