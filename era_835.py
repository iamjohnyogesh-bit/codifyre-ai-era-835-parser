"""835 (ERA) domain parser: envelopes in, structured remittance data out."""

from x12 import el, iter_transactions, money, num, split_segments
from carc_data import plb_desc, carc_desc, group_desc, CLAIM_STATUS


def _parse_cas(seg):
    """CAS segment: up to 6 (reason, amount, qty) triples after the group code."""
    adjs = []
    group = el(seg, 1)
    for i in range(2, len(seg), 3):
        reason = el(seg, i)
        if not reason:
            break
        adjs.append({
            "group": group,
            "group_desc": group_desc(group),
            "reason": reason,
            "reason_desc": carc_desc(reason),
            "amount": money(el(seg, i + 1)),
        })
    return adjs


def _svc_code(svc01):
    """'HC:99214:25' -> ('99214', ['25'])."""
    parts = svc01.split(":")
    code = parts[1] if len(parts) > 1 else parts[0]
    return code, [p for p in parts[2:] if p]


def parse_835_text(text):
    """Parse one or more 835 transactions from raw X12 text."""
    _, segments = split_segments(text)
    payments = []
    for txn in iter_transactions(segments):
        if txn.set_id != "835":
            continue
        payments.append(_parse_transaction(txn))
    return payments


def parse_835_file(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return parse_835_text(fh.read())


def _parse_transaction(txn):
    pay = {
        "control": txn.control,
        "payer": "",
        "payee": "",
        "payment_method": "",
        "payment_amount": 0.0,
        "check_number": "",
        "pay_date": "",
        "claims": [],
        "plb_adjustments": [],
    }
    current_claim = None
    current_line = None
    for seg in txn.segments:
        tag = seg[0]
        if tag == "BPR":
            pay["payment_amount"] = money(el(seg, 2))
            pay["payment_method"] = {"C": "ACH", "D": "Card", "B": "Non-payment data"}.get(el(seg, 3), el(seg, 3) or "ACH")
            pay["pay_date"] = el(seg, 16)
        elif tag == "TRN":
            pay["check_number"] = el(seg, 2)
        elif tag == "N1":
            if el(seg, 1) == "PR":
                pay["payer"] = el(seg, 2)
            elif el(seg, 1) == "PE":
                pay["payee"] = el(seg, 2)
        elif tag == "PLB":
            for i in range(3, len(seg), 2):
                ref = el(seg, i)
                amt = el(seg, i + 1)
                if not ref or amt == "":
                    break
                reason = ref.split(":")[0]
                pay["plb_adjustments"].append({
                    "reason": reason,
                    "reason_desc": plb_desc(reason),
                    "amount": money(amt),
                })
        elif tag == "CLP":
            current_claim = {
                "claim_id": el(seg, 1),
                "status": el(seg, 2),
                "status_desc": CLAIM_STATUS.get(el(seg, 2), "Unknown (" + el(seg, 2) + ")"),
                "charged": money(el(seg, 3)),
                "paid": money(el(seg, 4)),
                "patient_responsibility": money(el(seg, 5)),
                "payer_control": el(seg, 7),
                "patient": "",
                "patient_member_id": "",
                "adjustments": [],
                "service_lines": [],
            }
            pay["claims"].append(current_claim)
            current_line = None
        elif tag == "NM1" and current_claim is not None and el(seg, 1) == "QC":
            last, first = el(seg, 3), el(seg, 4)
            current_claim["patient"] = (first + " " + last).strip() or last
            current_claim["patient_member_id"] = el(seg, 9)
        elif tag == "SVC" and current_claim is not None:
            code, mods = _svc_code(el(seg, 1))
            units = 1
            for i in (5, 4):
                v = el(seg, i)
                if v and v.replace(".", "", 1).isdigit():
                    units = int(float(v))
                    break
            current_line = {
                "cpt": code,
                "modifiers": mods,
                "charged": money(el(seg, 2)),
                "paid": money(el(seg, 3)),
                "units": units,
                "adjustments": [],
            }
            current_claim["service_lines"].append(current_line)
        elif tag == "CAS" and current_claim is not None:
            (current_line["adjustments"] if current_line is not None
             else current_claim["adjustments"]).extend(_parse_cas(seg))
        elif tag == "AMT" and current_line is not None and el(seg, 1) == "AU":
            current_line["allowed"] = money(el(seg, 2))
    return pay


def summarize(payments):
    claims = [c for p in payments for c in p["claims"]]
    total_charged = sum(c["charged"] for c in claims)
    total_paid = sum(c["paid"] for c in claims)
    total_pr = sum(c["patient_responsibility"] for c in claims)
    adj_total = 0.0
    by_reason = {}
    for c in claims:
        adjs = list(c["adjustments"])
        for line in c["service_lines"]:
            adjs.extend(line["adjustments"])
        for a in adjs:
            adj_total += a["amount"]
            key = f'{a["group"]}-{a["reason"]}'
            row = by_reason.setdefault(key, {
                "code": key, "group_desc": a["group_desc"],
                "reason_desc": a["reason_desc"], "count": 0, "amount": 0.0})
            row["count"] += 1
            row["amount"] += a["amount"]
    by_status = {}
    for c in claims:
        row = by_status.setdefault(c["status_desc"], {"status": c["status_desc"],
                                                      "count": 0, "paid": 0.0})
        row["count"] += 1
        row["paid"] += c["paid"]
    by_payer = {}
    for p in payments:
        row = by_payer.setdefault(p["payer"] or "Unknown payer",
                                  {"payer": p["payer"] or "Unknown payer",
                                   "payments": 0, "amount": 0.0})
        row["payments"] += 1
        row["amount"] += p["payment_amount"]
    denied = [c for c in claims if c["status"] == "4"]
    return {
        "payments": len(payments),
        "claims": len(claims),
        "total_charged": round(total_charged, 2),
        "total_paid": round(total_paid, 2),
        "total_patient_responsibility": round(total_pr, 2),
        "total_adjustments": round(adj_total, 2),
        "denied_claims": len(denied),
        "denial_rate_pct": round(100.0 * len(denied) / len(claims), 1) if claims else 0.0,
        "paid_rate_pct": round(100.0 * total_paid / total_charged, 1) if total_charged else 0.0,
        "by_reason": sorted(by_reason.values(), key=lambda r: -r["amount"]),
        "by_status": sorted(by_status.values(), key=lambda r: -r["count"]),
        "by_payer": sorted(by_payer.values(), key=lambda r: -r["amount"]),
    }
