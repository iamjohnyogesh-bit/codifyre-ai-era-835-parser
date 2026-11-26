# Codifyre AI - ERA 835 Parser

> Turn raw X12 835 remittance files into clean CSVs, a payment reconciliation check and a dark/light dashboard. Zero dependencies.

**Codifyre AI** builds practical open-source tooling. This is Day 3 of the daily build series, after [denial analytics](https://github.com/iamjohnyogesh-bit/codifyre-ai-denial-management-analytics) (Day 1) and the [clean claim scrubber](https://github.com/iamjohnyogesh-bit/codifyre-ai-clean-claim-scrubber) (Day 2). Day 3 closes the loop: read what the payer actually paid.

## What it does

`era_cli.py` parses one or more 835 transactions (multiple payers per file supported) and produces:

- **claims.csv**: one row per claim (status, charged, paid, patient responsibility, total adjustments)
- **service_lines.csv**: one row per service line (CPT, modifiers, units, allowed, paid, CO/PR/OA adjustments)
- **denials.csv**: denied claims with group code, CARC and plain-English reason
- **Reconciliation**: checks every payment's BPR amount against claim payments minus PLB provider adjustments, and flags any difference
- **summary.json** and an **HTML dashboard** (dark default, light toggle remembered per visitor)

## Segments handled

`ISA` (delimiter auto-detection), `ST/SE`, `BPR`, `TRN`, `N1` (PR/PE), `CLP`, `NM1*QC`, `SVC` (with modifiers and units), `CAS` (up to 6 reason/amount pairs), `AMT*AU` (allowed), `PLB`.

CARC, claim status, group code and PLB reason descriptions live in `carc_data.py`. Unknown codes pass through as `CARC <code>` rather than failing. Official code lists: https://x12.org/codes/claim-adjustment-reason-codes

## Quickstart

```bash
python3 gen_sample_835.py        # writes data/sample_835.txt (2 payments, 12 claims)
python3 era_cli.py data/sample_835.txt --out out --json out/summary.json --html out/dashboard.html
python3 -m unittest discover -s tests -v   # 13 tests
```

Use it on a real file with `python3 era_cli.py your_file.835 --out out`.

## Sample output

```
ERA 835 PARSER - REMITTANCE REPORT
Payments         : 2
Claims           : 12 (2 denied, 16.7%)
Charged          : $5,986.00
Paid             : $4,283.00 (71.6% of charges)
Patient resp.    : $350.00
Adjustments      : $1,703.00

-- Payment reconciliation
  [OK ] CGS MEDICARE      BPR $ 2,488.00  expected $ 2,488.00  diff +0.00
  [OK ] AETNA COMMERCIAL  BPR $ 1,745.00  expected $ 1,745.00  diff +0.00
```

## Layout

```
x12.py            delimiter detection, segment splitting, ST..SE iteration
era_835.py        835 domain parser and summary math
carc_data.py      CARC / status / group / PLB reference data
era_cli.py        CLI, CSV exports, reconciliation
era_dashboard.py  HTML dashboard with dark/light toggle
gen_sample_835.py deterministic synthetic 835 generator
tests/            13 unit tests
data/sample_835.txt
```

Sample data is synthetic. No real patient information.

## License

MIT, see [LICENSE](LICENSE). Built by **Codifyre AI**.
