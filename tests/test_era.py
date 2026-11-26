import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import gen_sample_835
from era_835 import parse_835_text, summarize
from era_cli import reconcile, claim_rows, line_rows, denial_rows, main
from era_dashboard import render
from x12 import detect_delimiters


class EraTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = gen_sample_835.build()
        cls.payments = parse_835_text(cls.text)
        cls.summary = summarize(cls.payments)

    def test_delimiters(self):
        d = detect_delimiters(self.text)
        self.assertEqual((d.element, d.component, d.segment), ("*", ":", "~"))

    def test_counts(self):
        self.assertEqual(len(self.payments), 2)
        self.assertEqual(self.summary["claims"], 12)
        self.assertEqual(self.summary["denied_claims"], 2)
        self.assertEqual(self.summary["denial_rate_pct"], 16.7)

    def test_totals(self):
        self.assertEqual(self.summary["total_charged"], 5986.00)
        self.assertEqual(self.summary["total_paid"], 4283.00)

    def test_modifiers_and_units(self):
        line = self.payments[0]["claims"][4]["service_lines"][0]
        self.assertEqual(line["cpt"], "97140")
        self.assertEqual(line["modifiers"], ["GP"])
        self.assertEqual(line["units"], 2)

    def test_cas_groups(self):
        c = self.payments[0]["claims"][1]
        adjs = c["service_lines"][0]["adjustments"]
        self.assertEqual({(a["group"], a["reason"]) for a in adjs}, {("CO", "45"), ("PR", "1")})

    def test_plb(self):
        plb = self.payments[0]["plb_adjustments"]
        self.assertEqual(plb[0]["reason"], "WO")
        self.assertEqual(plb[0]["amount"], 50.0)

    def test_reconcile_balanced(self):
        self.assertTrue(all(r["balanced"] for r in reconcile(self.payments)))

    def test_reconcile_detects_mismatch(self):
        bad = self.text.replace("BPR*I*1745.00", "BPR*I*1700.00")
        recon = reconcile(parse_835_text(bad))
        self.assertFalse(recon[1]["balanced"])
        self.assertEqual(recon[1]["difference"], -45.0)

    def test_denials(self):
        rows = list(denial_rows(self.payments))
        self.assertEqual({r["carc"] for r in rows}, {"197", "18"})

    def test_csv_rows(self):
        self.assertEqual(len(list(claim_rows(self.payments))), 12)
        self.assertEqual(len(list(line_rows(self.payments))), 14)

    def test_non_835_ignored(self):
        self.assertEqual(parse_835_text("ISA*00*not an edi file"), [])

    def test_dashboard(self):
        page = render({"summary": self.summary, "reconciliation": reconcile(self.payments)})
        for marker in ("Codifyre AI", 'id="theme-toggle"', "body.light", "Payment reconciliation"):
            self.assertIn(marker, page)

    def test_cli_end_to_end(self):
        tmp = tempfile.mkdtemp()
        src = os.path.join(tmp, "in.txt")
        with open(src, "w") as fh:
            fh.write(self.text)
        rc = main([src, "--out", os.path.join(tmp, "o"), "--json", os.path.join(tmp, "s.json"),
                   "--html", os.path.join(tmp, "d.html")])
        self.assertEqual(rc, 0)
        for f in ("o/claims.csv", "o/service_lines.csv", "o/denials.csv", "s.json", "d.html"):
            self.assertTrue(os.path.getsize(os.path.join(tmp, f)) > 0, f)


if __name__ == "__main__":
    unittest.main()
