# NovaCart Human Escalation Policy

## 1. When to Escalate to Human Support
Autonomous AI agents must promptly transfer a customer interaction to a human specialist in any of the following circumstances:
- **Explicit Customer Request**: The customer explicitly requests a human agent, supervisor, or live representative.
- **Low Confidence**: The overall task confidence score falls below the 0.75 threshold.
- **Repeated Failures**: Two or more tool calls or API operations fail consecutively.
- **High-Value Actions**: Any refund or credit exceeding $500.00.
- **Complex Disputes**: Suspicion of fraud, legal threats, disputed chargebacks, or harassment.
- **Ambiguous Policy Application**: When multiple conflicting policies apply or order status documentation is missing.

## 2. Handoff Protocol
- The Escalation Agent must compile a comprehensive dossier:
  1. Customer Profile and Tier
  2. Original User Request and Detected Intent
  3. Action Plan and Completed Steps
  4. Tools executed with exact input/output payloads
  5. Specific reason for escalation
  6. Recommended next action for the human agent
- A unique Ticket ID (e.g. `TICK-xxxxx`) is created in the human escalation ledger.
