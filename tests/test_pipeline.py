#!/usr/bin/env python3
"""
v6.5 回歸測試（2026-09-28）：改 scripts/ 底下任何程式前後都跑一次。

  python3 -m unittest discover -s tests -v

測試資料：
  tests/fixtures/reports/*.md                    過去 11 份日報原稿（2026-09-20～09-28，含多種舊寫法）
  tests/fixtures/expected_reports.json           每份的日期、各區則數、文末統計（解析結果快照）
  tests/fixtures/igamingtoday-2026-09-28.md      iGamingToday 列表頁（Huff N´Puff 漏收那天）
  tests/fixtures/slotslaunch-calendar-2026-09-28.html  SlotsLaunch 上線日曆
新增一份日報當測試資料：把 .md 複製進 reports/，再重跑快照（見 RUNBOOK「回歸測試」）。
"""
import glob
import json
import os
import re
import sys
import unittest
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures")
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import finalize_report as F  # noqa: E402
import harvest as H  # noqa: E402
import inventory as INV  # noqa: E402
import report_lib as R  # noqa: E402


def theme_compatible(s):
    """與 main 分支 report_theme.py 的 compatible() 同一條件（網站樣式開關靠它判斷能不能套）。"""
    return all(k in s for k in ("<header>", 'class="date"')) and re.search(r'class="card c[1-5]"', s)


class TestReports(unittest.TestCase):
    def setUp(self):
        self.expected = json.load(open(os.path.join(FIX, "expected_reports.json"), encoding="utf-8"))
        self.files = sorted(glob.glob(os.path.join(FIX, "reports", "*.md")))

    def test_fixture_count(self):
        self.assertEqual(len(self.files), len(self.expected))

    def test_parse_matches_snapshot(self):
        for f in self.files:
            with self.subTest(f=os.path.basename(f)):
                with open(f, encoding="utf-8") as fh:
                    r = R.parse_md(fh.read())
                exp = self.expected[os.path.basename(f)]
                self.assertEqual(r["date"], exp["date"])
                self.assertEqual({s["cat"]: len(s["items"]) for s in r["sections"] if s["items"]}, exp["counts"])
                self.assertEqual(r["stats"], exp["stats"])

    def test_every_item_has_source_and_date(self):
        for f in self.files:
            r = R.parse_md(open(f, encoding="utf-8").read())
            for s in r["sections"]:
                for it in s["items"]:
                    with self.subTest(f=os.path.basename(f), item=it["title"][:30]):
                        self.assertTrue(it["sources"], "沒解析到來源連結")
                        self.assertRegex(it["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_render_is_theme_compatible(self):
        for f in self.files:
            r = R.parse_md(open(f, encoding="utf-8").read())
            if not any(s["items"] for s in r["sections"]):
                continue
            with self.subTest(f=os.path.basename(f)):
                out = R.render_html(r)
                self.assertTrue(theme_compatible(out))
                self.assertIn('class="stats-line"', out)
                self.assertNotIn("<p>---</p>", out)
                self.assertEqual(out.count('class="stats-line"'), 1)
                n = sum(len(s["items"]) for s in r["sections"])
                self.assertEqual(len(re.findall(r'class="card c[1-5]"', out)), n)

    def test_internal_section_not_rendered(self):
        r = R.parse_md(open(os.path.join(FIX, "reports", "2026-09-28-igaming-report.md"), encoding="utf-8").read())
        self.assertIn("來源日期紀錄", r["internal"])
        self.assertNotIn("來源日期紀錄", R.render_html(r))


class TestFuzzy(unittest.TestCase):
    SAME = [("Huff N' Puff Mansion", "Light & Wonder", "Huff N´Puff Mansion", "L&W"),
            ("Big Bass Vegas 1000", "Pragmatic Play", "Big Bass Vegas 1000 Slot", "Pragmatic"),
            ("The Traitors™: Fortune", "Games Global", "The Traitors: Fortune", ""),
            ("Lucky Mischief", "PG Soft", "Lucky Mischief", "PG"),
            ("Bao Zhu Zhao Fu Grand", "Light & Wonder", "Bao Zhu Zhao Fu Grand", "SG")]
    DIFF = [("Money Train 4", "Relax", "Money Train 5", "Relax Gaming"),
            ("Thor's Rage", "Red Tiger", "Thor's Rage 2", "Red Tiger"),
            ("Sugar Rush", "Pragmatic", "Sugar Rush", "Hacksaw"),
            ("Fortune Tiger", "PG Soft", "Fortune Ox", "PG Soft")]

    def test_same(self):
        for a in self.SAME:
            with self.subTest(a=a):
                self.assertTrue(R.same_item(*a))

    def test_diff(self):
        for a in self.DIFF:
            with self.subTest(a=a):
                self.assertFalse(R.same_item(*a))


class TestDateRules(unittest.TestCase):
    def run_check(self, cat, d, label="", day="2026-09-29"):
        qa = F.QA()
        F.check_date({"date": d, "label": label}, cat, date.fromisoformat(day), "t", qa)
        return qa

    def test_same_day_ok(self):
        self.assertFalse(self.run_check("cat3", "2026-09-28").errors)

    def test_old_news_blocked(self):
        self.assertTrue(self.run_check("cat3", "2026-09-25").errors)

    def test_inventory_fresh(self):
        self.assertFalse(self.run_check("cat1", "2026-09-23", "📦 近期新作（9/23 首見）").errors)
        self.assertTrue(self.run_check("cat1", "2026-09-20", "📦 近期新作（9/20 首見）").errors)
        self.assertTrue(self.run_check("cat3", "2026-09-25", "📦（9/25）").errors)

    def test_future_blocked(self):
        self.assertTrue(self.run_check("cat1", "2026-10-01").errors)


class TestHarvestParsers(unittest.TestCase):
    def test_igamingtoday(self):
        r = H.parse_igamingtoday(open(os.path.join(FIX, "igamingtoday-2026-09-28.md"), encoding="utf-8").read())
        titles = [x["title"] for x in r]
        self.assertGreaterEqual(len(r), 10)
        self.assertTrue(any("Huff N´Puff" in t for t in titles), "漏掉 Huff N´Puff（9/28 的漏收案例）")
        huff = next(x for x in r if "Huff N´Puff" in x["title"])
        self.assertEqual(huff["dt"].date().isoformat(), "2026-09-27")

    def test_slotslaunch(self):
        body = open(os.path.join(FIX, "slotslaunch-calendar-2026-09-28.html"), encoding="utf-8").read()
        r, err = H.fetch_slotslaunch(body)
        self.assertIsNone(err)
        self.assertGreaterEqual(len(r), 40)
        byname = {x["title"]: x for x in r}
        self.assertIn("Gates of Olympus 2500 — Pragmatic Play", byname)
        self.assertEqual(byname["Gates of Olympus 2500 — Pragmatic Play"]["dt"].date().isoformat(), "2026-09-28")
        self.assertIn("3 Lucky Monkeys — BGaming", byname)
        self.assertEqual(len({x["url"] for x in r}), len(r), "同一款重複")


class TestSitemap(unittest.TestCase):
    def test_playngo_sitemap(self):
        from datetime import datetime
        body = open(os.path.join(FIX, "playngo-sitemap-2026-10-11.xml"), encoding="utf-8").read()
        orig = H.sh
        H.sh = lambda url, timeout=20: body
        try:
            r, err = H.fetch_sitemap({"name": "Play'n GO", "endpoint": "x"}, datetime(2026, 10, 1, tzinfo=H.TPE))
        finally:
            H.sh = orig
        self.assertIsNone(err)
        games = {x["title"]: x for x in r if x["force_cat"] == "cat1"}
        self.assertIn("Redtail Robber Cash Vault Heist — Play'n GO", games)
        self.assertEqual(games["Redtail Robber Cash Vault Heist — Play'n GO"]["dt"].date().isoformat(), "2026-10-08")
        self.assertFalse(any(x["dt"].year == 9999 for x in r))


class TestPageMeta(unittest.TestCase):
    def test_parse(self):
        import page_meta as P
        body = ('<html><head><meta property="og:title" content="New Slot &amp; Co"/>'
                '<meta property="article:published_time" content="2026-10-10T08:00:00+00:00"/>'
                '<meta content="https://x.com/a.jpg" property="og:image"/></head>'
                '<body><article>' + "<p>" + "內文段落" * 30 + "</p>" * 1 + '</article></body></html>')
        self.assertEqual(P.meta(body, "og:title"), "New Slot & Co")
        self.assertEqual(P.meta(body, "og:image"), "https://x.com/a.jpg")
        self.assertEqual(P.published(body), ("2026-10-10T08:00:00+00:00", "metadata"))
        self.assertTrue(len(P.main_text(body, 3000)) > 40)

    def test_jsonld_date(self):
        import page_meta as P
        body = '<script type="application/ld+json">{"dateModified":"2026-10-11","datePublished":"2026-10-09T01:00:00Z"}</script>'
        self.assertEqual(P.published(body)[0], "2026-10-09T01:00:00Z")


class TestTiers(unittest.TestCase):
    def tier(self, remaining, end="2026-10-14", today="2026-09-28"):
        return H.pick_tier({"remaining": remaining, "plan": 1000, "period_end": end}, date.fromisoformat(today))[0][0]

    def test_levels(self):
        self.assertIn("充裕", self.tier(599))           # (599-20)/16 = 36
        self.assertIn("標準", self.tier(400))           # 23
        self.assertIn("節約", self.tier(290))           # 16
        self.assertIn("保命", self.tier(250))           # 14
        self.assertIn("保命", self.tier(99, today="2026-10-13"))   # 低於 100 一律保命

    def test_no_credit_info(self):
        self.assertIn("標準", H.pick_tier(None, date(2026, 9, 28))[0][0])


class TestInventory(unittest.TestCase):
    def test_placeholder(self):
        tbc = {"title": "Nigel of Ra", "first_seen": "2026-09-26",
               "sources": [{"name": "BigWinBoard（TBC，頁面 metadata 顯示 2026-09-16 舊日期）", "url": "x"}]}
        self.assertTrue(INV.is_placeholder(tbc))
        self.assertFalse(INV.is_placeholder({**tbc, "release_date": "2026-10-02"}))
        ok = {"title": "Aquamasters", "first_seen": "2026-09-23", "sources": [{"name": "BigWinBoard", "url": "x"}]}
        self.assertFalse(INV.is_placeholder(ok))


if __name__ == "__main__":
    unittest.main()
