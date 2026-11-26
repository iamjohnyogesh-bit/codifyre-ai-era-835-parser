"""Curated CARC / RARC and claim-status reference data.

CARC/RARC codes are maintained by the X12/HL7 code committee:
  https://x12.org/codes/claim-adjustment-reason-codes
This module ships the codes that account for the vast majority of real
remittance volume; unknown codes are passed through with their raw value.
"""

CLAIM_STATUS = {
    "1": "Processed as Primary",
    "2": "Processed as Secondary",
    "3": "Processed as Tertiary",
    "4": "Denied",
    "19": "Processed as Primary, Forwarded to Additional Payer(s)",
    "20": "Processed as Secondary, Forwarded to Additional Payer(s)",
    "21": "Processed as Tertiary, Forwarded to Additional Payer(s)",
    "22": "Reversal of Previous Payment",
}

GROUP_CODES = {
    "CO": "Contractual Obligation",
    "CR": "Correction and Reversal",
    "OA": "Other Adjustment",
    "PI": "Payer Initiated Reduction",
    "PR": "Patient Responsibility",
}

CARC = {
    "1": "Deductible amount",
    "2": "Coinsurance amount",
    "3": "Co-payment amount",
    "4": "Procedure code inconsistent with modifier used",
    "5": "Procedure code/bill type inconsistent with place of service",
    "11": "Diagnosis inconsistent with procedure",
    "16": "Claim/service lacks information needed for adjudication",
    "18": "Exact duplicate claim/service",
    "22": "This care may be covered by another payer per coordination of benefits",
    "23": "Impact of prior payer(s) adjudication",
    "27": "Expenses incurred after coverage terminated",
    "29": "The time limit for filing has expired",
    "45": "Charge exceeds fee schedule/maximum allowable or contracted arrangement",
    "50": "These are non-covered services (not deemed a medical necessity)",
    "96": "Non-covered charge(s)",
    "97": "The benefit for this service is included in the payment/allowance for another service",
    "109": "Claim/service not covered by this payer/contractor",
    "119": "Benefit maximum for this time period has been reached",
    "129": "Prior processing information appears incorrect",
    "151": "Payment adjusted because information submitted does not support this many services",
    "197": "Precertification/authorization/notification absent",
    "B1": "Non-covered visits",
}


PLB_REASONS = {
    "WO": "Overpayment recovery",
    "FB": "Forwarding balance",
    "L6": "Interest owed",
    "72": "Authorized return",
    "CS": "Adjustment",
    "IR": "Internal revenue service withholding",
    "50": "Late charge",
    "J1": "Nonreimbursable",
}


def plb_desc(code):
    return PLB_REASONS.get(code, "PLB " + code)


def carc_desc(code):
    return CARC.get(code, "CARC " + code)


def group_desc(code):
    return GROUP_CODES.get(code, code)
