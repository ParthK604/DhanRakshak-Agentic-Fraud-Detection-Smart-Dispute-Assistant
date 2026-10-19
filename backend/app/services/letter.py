import re

from app.models.dispute import DisputeLetter, EvidencePack, RefundCalculation


def template_letter(issue_type: str, evidence: EvidencePack, refund: RefundCalculation) -> DisputeLetter:
    ids = ", ".join(item.txn_id for item in evidence.matched_txns)
    amounts = ", ".join(f"{item.amount:.2f} {item.currency}" for item in evidence.matched_txns)
    subject = f"Request for review: {issue_type.replace('_', ' ')}"
    body = (
        f"Hello, I am requesting a review of a {issue_type.replace('_', ' ')} involving "
        f"transaction(s) {ids}. The recorded charge amount(s) are {amounts}. "
        f"Based on the attached evidence, I request the applicable refund. {refund.disclaimer}"
    )
    return DisputeLetter(subject=subject, body=body, grounded=True)


def verify_letter_grounding(letter: DisputeLetter, evidence: EvidencePack) -> bool:
    text = f"{letter.subject} {letter.body}"
    valid_ids = {item.txn_id for item in evidence.matched_txns}
    valid_amounts = {f"{item.amount:.2f}" for item in evidence.matched_txns}
    ids = set(re.findall(r"\b(?:txn|seed|simulated)-[A-Za-z0-9-]+\b", text, re.I))
    amounts = set(re.findall(r"\b\d+\.\d{2}\b", text))
    return all(item in valid_ids for item in ids if item.lower() not in {"request", "review"}) and all(
        amount in valid_amounts for amount in amounts
    )
