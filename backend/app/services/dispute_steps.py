from app.models.dispute import ResolutionStep


def resolution_steps(issue_type: str, status: str = "draft") -> list[ResolutionStep]:
    return [
        ResolutionStep(order=1, title="Review the evidence", detail="Check the transaction IDs, dates, amounts, and merchant details before submitting.", owner="user", status="current" if status == "draft" else "complete"),
        ResolutionStep(order=2, title="Contact the merchant", detail="Ask the merchant to correct or refund the charge and keep the response as evidence.", owner="merchant"),
        ResolutionStep(order=3, title="Submit through PayPal", detail="If unresolved, submit the prepared evidence through the PayPal Resolution Center or the enabled Disputes API.", owner="paypal"),
        ResolutionStep(order=4, title="Monitor the case", detail="PayPal and the merchant review the evidence; respond to any requested information.", owner="paypal"),
    ]
