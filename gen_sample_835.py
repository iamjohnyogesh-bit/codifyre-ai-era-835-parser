#!/usr/bin/env python3
"""Generate a realistic synthetic X12 835 (ERA) remittance file.

Deterministic output: two payments from two payers, 12 claims total,
covering paid-in-full claims, contractual (CO-45) write-offs, patient
responsibility (PR-1/2/3), bundling (CO-97), a duplicate denial (CO-18),
an authorization denial (CO-197) and one provider-level recoupment (PLB WO).
"""

ISA = ("ISA*00*          *00*          *ZZ*CLEARHOUSE     *ZZ*CITYCLINIC    "
       "*261124*0900*^*00501*000000001*0*T*:~")


def claim(claim_id, status, charged, paid, pr, ctrl, patient, member, lines):
    """lines: list of (svc01, charged, paid, units, dos, [cas...], allowed)"""
    segs = [f"CLP*{claim_id}*{status}*{charged:.2f}*{paid:.2f}*{pr:.2f}*12*{ctrl}*11*1",
            f"NM1*QC*1*{patient[1]}*{patient[0]}****MI*{member}"]
    for svc01, lcharged, lpaid, units, dos, cas_list, allowed in lines:
        segs.append(f"SVC*{svc01}*{lcharged:.2f}*{lpaid:.2f}**{units}")
        segs.append(f"DTM*472*{dos}")
        for cas in cas_list:
            segs.append(cas)
        if allowed is not None:
            segs.append(f"AMT*AU*{allowed:.2f}")
    return segs


def payment(bpr_amount, trn, payer, claims, plb=None):
    segs = [f"BPR*I*{bpr_amount:.2f}*C*ACH*CCP*01*999888777*DA*1234567890**01*011000028*DA*5554443332*20261124",
            f"TRN*1*{trn}*1998888777",
            "REF*EV*CITYCLINIC",
            "DTM*405*20261124",
            f"N1*PR*{payer}",
            "N3*PO BOX 7070",
            "N4*NASHVILLE*TN*37202",
            "PER*BL*PROVIDER SERVICES*TE*8005550142",
            "N1*PE*CITY CLINIC LLC*XX*1234567893",
            "LX*1"]
    for c in claims:
        segs.extend(c)
    if plb:
        segs.append(f"PLB*1234567893*20261231*{plb}")
    return segs


def build():
    med = payer_medicare_claims()
    aetna = payer_aetna_claims()
    payments = [
        ("0001", payment(2488.00, "EFT00045123", "CGS MEDICARE", med,
                         plb="WO:441202*50.00")),  # prior overpayment offset
        ("0002", payment(1745.00, "CHK00099887", "AETNA COMMERCIAL", aetna)),
    ]
    segs = ["GS*HP*CLEARHOUSE*CITYCLINIC*20261124*0900*1*X*005010X221A1"]
    for ctrl, body in payments:
        segs.append(f"ST*835*{ctrl}*005010X221A1")
        segs.extend(body)
        segs.append(f"SE*{len(body) + 2}*{ctrl}")
    segs += ["GE*2*1", "IEA*1*000000001"]
    return ISA + "\n" + "~\n".join(segs) + "~\n"


def payer_medicare_claims():
    return [
        claim("CLM9001", "1", 300.00, 210.00, 0.00, "MC9001", ("JOHN", "DOE"), "1EG4TE5MK73",
              [("HC:99214", 300.00, 210.00, 1, "20261101",
                ["CAS*CO*45*90.00"], 210.00)]),
        claim("CLM9002", "1", 180.00, 96.00, 24.00, "MC9002", ("JANE", "SMITH"), "2EG4TE5MK71",
              [("HC:99213", 180.00, 96.00, 1, "20261102",
                ["CAS*CO*45*60.00", "CAS*PR*1*24.00"], 120.00)]),
        claim("CLM9003", "1", 450.00, 360.00, 0.00, "MC9003", ("RAJU", "KUMAR"), "3EG4TE5MK79",
              [("HC:93000", 150.00, 120.00, 1, "20261103", ["CAS*CO*45*30.00"], 120.00),
               ("HC:71046", 300.00, 240.00, 1, "20261103", ["CAS*CO*45*60.00"], 240.00)]),
        claim("CLM9004", "1", 220.00, 176.00, 44.00, "MC9004", ("MEERA", "NAIR"), "4EG4TE5MK75",
              [("HC:85025", 220.00, 176.00, 1, "20261103",
                ["CAS*PR*2*44.00"], 220.00)]),
        claim("CLM9005", "1", 520.00, 416.00, 0.00, "MC9005", ("ARUN", "PILLAI"), "5EG4TE5MK77",
              [("HC:97140:GP", 260.00, 208.00, 2, "20261104", ["CAS*CO*45*104.00"], 416.00),
               ("HC:97010", 0.00, 0.00, 1, "20261104", ["CAS*CO*97*0.00"], 0.00)]),
        claim("CLM9006", "1", 900.00, 720.00, 90.00, "MC9006", ("DIVYA", "RAO"), "6EG4TE5MK72",
              [("HC:27447", 900.00, 720.00, 1, "20261105",
                ["CAS*CO*45*90.00", "CAS*PR*1*90.00"], 810.00)]),
        claim("CLM9007", "1", 700.00, 560.00, 0.00, "MC9007", ("VIKRAM", "SHAH"), "7EG4TE5MK70",
              [("HC:99285:25", 700.00, 560.00, 1, "20261106", ["CAS*CO*45*140.00"], 560.00)]),
    ]


def payer_aetna_claims():
    return [
        claim("CLM9101", "1", 260.00, 208.00, 0.00, "AE9101", ("KAVYA", "MENON"), "M1002001",
              [("HC:99213", 260.00, 208.00, 1, "20261102", ["CAS*CO*45*52.00"], 208.00)]),
        claim("CLM9102", "1", 380.00, 304.00, 38.00, "AE9102", ("SANJAY", "VERMA"), "M1002002",
              [("HC:80053", 380.00, 304.00, 1, "20261103",
                ["CAS*CO*45*38.00", "CAS*PR*3*38.00"], 342.00)]),
        claim("CLM9103", "4", 275.00, 0.00, 0.00, "AE9103", ("PRIYA", "IYER"), "M1002003",
              [("HC:99214", 275.00, 0.00, 1, "20261104",
                ["CAS*CO*197*275.00"], 0.00)]),
        claim("CLM9104", "4", 260.00, 0.00, 0.00, "AE9104", ("KAVYA", "MENON"), "M1002001",
              [("HC:99213", 260.00, 0.00, 1, "20261104",
                ["CAS*CO*18*260.00"], 0.00)]),
        claim("CLM9105", "1", 1541.00, 1233.00, 154.00, "AE9105", ("ROHAN", "GUPTA"), "M1002005",
              [("HC:29881", 1541.00, 1233.00, 1, "20261105",
                ["CAS*CO*45*154.00", "CAS*PR*2*154.00"], 1387.00)]),
    ]


def main():
    text = build()
    with open("data/sample_835.txt", "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Wrote {len(text)} bytes to data/sample_835.txt")


if __name__ == "__main__":
    main()
