#!/usr/bin/env python3
"""Codifyre AI - ERA 835 Parser CLI.

Parse X12 835 remittance files into CSVs, a reconciliation report, a JSON
summary and an HTML dashboard.

    python3 era_cli.py data/sample_835.txt --out out --json out/summary.json --html out/dashboard.html
"""

import argparse
import csv
import json
import os
import sys

from era_835 import parse_835_file, summarize


def reconcile(payments):
    """BPR payment must equal sum(CLP paid) minus provider-level adjustments."""
    rows = []
    for p in payments:
        paid = round(sum(c["paid"] for c in p["claims"]), 2)
        plb = round(sum(a["amount"] for a in p["plb_adjustments"]), 2)
        expected = round(paid - plb, 2)
        diff = round(p["payment_amount"] - expected, 2)
        rows.append({
            "trace": p["check_number"], "payer": p["payer"],
            "payment_amount": p["payment_amount"], "claims_paid": paid,
            "plb_adjustments": plb, "expected": expected, "difference": diff,
            "balanced": abs(diff) < 0.005,
        })
    return rows


def claim_rows(payments):
    for p in payments:
        for c in p["claims"]:
            yield {
                "trace": p["check_number"], "payer": p["payer"], "claim_id": c["claim_id"],
                "patient": c["patient"], "member_id": c["patient_member_id"],
                "status": c["status_desc"], "charged": c["charged"], "paid": c["paid"],
                "patient_responsibility": c["patient_responsibility"],
                "adjustment_total": round(sum(a["amount"] for a in c["adjustments"]) + sum(
                    a["amount"] for l in c["service_lines"] for a in l["adjustments"]), 2),
            }


def line_rows(payments):
    for p in payments:
        for c in p["claims"]:
            for l in c["service_lines"]:
                adj = "; ".join(f'{a["group"]}-{a["reason"]} {a["amount"]:.2f}' for a in l["adjustments"])
                yield {
                    "claim_id": c["claim_id"], "cpt": l["cpt"], "modifiers": " ".join(l["modifiers"]),
                    "units": l["units"], "charged": l["charged"], "allowed": l.get("allowed", ""),
                    "paid": l["paid"], "adjustments": adj,
                }


def denial_rows(payments):
    for p in payments:
        for c in p["claims"]:
            if c["status"] != "4":
                continue
            adjs = list(c["adjustments"]) + [a for l in c["service_lines"] for a in l["adjustments"]]
            for a in adjs or [{"group": "", "reason": "", "reason_desc": "No CAS reason given", "amount": 0.0}]:
                yield {
                    "claim_id": c["claim_id"], "payer": p["payer"], "patient": c["patient"],
                    "charged": c["charged"], "group": a["group"], "carc": a["reason"],
                    "reason": a["reason_desc"], "amount": a["amount"],
                }


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        return 0
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return len(rows)


def console(summary, recon):
    print("=" * 64)
    print("ERA 835 PARSER - REMITTANCE REPORT")
    print("=" * 64)
    print(f"Payments         : {summary['payments']}")
    print(f"Claims           : {summary['claims']} ({summary['denied_claims']} denied, {summary['denial_rate_pct']}%)")
    print(f"Charged          : ${summary['total_charged']:,.2f}")
    print(f"Paid             : ${summary['total_paid']:,.2f} ({summary['paid_rate_pct']}% of charges)")
    print(f"Patient resp.    : ${summary['total_patient_responsibility']:,.2f}")
    print(f"Adjustments      : ${summary['total_adjustments']:,.2f}")
    print("\n-- Top adjustment reasons " + "-" * 36)
    for r in summary["by_reason"][:8]:
        print(f"  {r['code']:<8} {r['count']:>3}  ${r['amount']:>9,.2f}  {r['reason_desc'][:48]}")
    print("\n-- Payment reconciliation " + "-" * 36)
    for r in recon:
        flag = "OK " if r["balanced"] else "OFF"
        print(f"  [{flag}] {r['payer'][:22]:<22} BPR ${r['payment_amount']:>9,.2f}  "
              f"expected ${r['expected']:>9,.2f}  diff {r['difference']:+.2f}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Parse X12 835 ERA files")
    ap.add_argument("file", help="835 file path")
    ap.add_argument("--out", help="directory for claims/lines/denials CSVs")
    ap.add_argument("--json", help="write JSON summary here")
    ap.add_argument("--html", help="write HTML dashboard here")
    args = ap.parse_args(argv)

    payments = parse_835_file(args.file)
    if not payments:
        print("No 835 transactions found in file.", file=sys.stderr)
        return 1
    summary = summarize(payments)
    recon = reconcile(payments)
    console(summary, recon)

    if args.out:
        os.makedirs(args.out, exist_ok=True)
        n1 = write_csv(os.path.join(args.out, "claims.csv"), claim_rows(payments))
        n2 = write_csv(os.path.join(args.out, "service_lines.csv"), line_rows(payments))
        n3 = write_csv(os.path.join(args.out, "denials.csv"), denial_rows(payments))
        print(f"\nCSV written to {args.out}/: claims={n1} service_lines={n2} denials={n3}")
    payload = {"summary": summary, "reconciliation": recon, "payments": payments}
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(f"JSON written to {args.json}")
    if args.html:
        from era_dashboard import render
        os.makedirs(os.path.dirname(os.path.abspath(args.html)), exist_ok=True)
        with open(args.html, "w", encoding="utf-8") as fh:
            fh.write(render(payload))
        print(f"Dashboard written to {args.html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
