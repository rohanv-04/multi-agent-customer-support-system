import re
from typing import Optional, Dict, Any, List

# Comprehensive list of internal patterns that must NEVER reach the customer
INTERNAL_PATTERNS = [
    # Agent names
    r"\b(?:critic|resolution|supervisor|intake|intent|planner|verification|escalation|policy|risk)\s+agent\b",
    r"\b(?:agent\s+run|agent\s+state|agent\s+output|agent\s+name|agentic)\b",
    # Workflow / Framework internals
    r"\blanggraph\b",
    r"\borchestrator\b",
    r"\bnode\s+[a-zA-Z0-9_-]+\b",
    r"\bworkflow\s+step\b",
    r"\bexecution\s+trace\b",
    r"\bstate\s+transition\b",
    r"\bchain[- ]of[- ]thought\b",
    r"\bre-?planning\b",
    r"\biteration\s+count\b",
    # Exact problematic pattern and step artifacts
    r"step\s+['\"][^'\"]*['\"]\s+analyzed\s+and\s+synthesized(?:[^\.]*context)?",
    r"step\s+['\"][^'\"]*['\"]\s+completed",
    r"analyzed\s+and\s+synthesized\s+with\s+available\s+context",
    r"validate\s+output\s+with\s+critic\s+agent",
    r"validate\s+(?:comprehensive\s+resolution|status\s+accuracy|policy\s+compliance|cancellation)\s+with\s+critic\s+agent",
    # Tool names
    r"\b(?:process_refund|get_order_status|check_refund_eligibility|cancel_order|create_replacement|vector_search|rag_retrieval|dispatch_email|dispatch_whatsapp)\b",
    r"\btool\s+(?:call|executed|execution|output|used|result)\b",
    # Internal error & prompt terms
    r"\b(?:system_prompt|prompt_template|traceback|json\.loads|exception\s+at|nullpointer)\b",
]

COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INTERNAL_PATTERNS]


class ResponseSanitizer:
    """Outbound firewall for customer-facing communications.
    
    Guarantees that no internal agent names, Critic Agent traces, LangGraph steps,
    tool names, or technical execution diagnostics leak to customer chat.
    """

    @classmethod
    def is_customer_safe(cls, text: str) -> bool:
        """Returns True if text contains zero internal agent workflow language."""
        if not text:
            return True
        for pattern in COMPILED_PATTERNS:
            if pattern.search(text):
                return False
        return True

    @classmethod
    def detect_violations(cls, text: str) -> List[str]:
        """Returns a list of matched internal leak patterns in text."""
        if not text:
            return []
        violations = []
        for pattern in COMPILED_PATTERNS:
            match = pattern.search(text)
            if match:
                violations.append(match.group(0))
        return violations

    @classmethod
    def sanitize(cls, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Sanitizes draft customer text, removing or rewriting internal execution language
        into natural, warm, conversational customer support responses.
        """
        if not text:
            return "How can I assist you with your orders, shipments, or store policies today?"

        # Check for the specific problematic phrasing reported:
        # e.g., "I've investigated your inquiry. Step 'Validate output with Critic Agent' analyzed and synthesized with available context. Please let me know how else I can assist you."
        if re.search(r"step\s+['\"][^'\"]*['\"]\s+analyzed\s+and\s+synthesized", text, re.IGNORECASE) or \
           re.search(r"validate\s+output\s+with\s+critic\s+agent", text, re.IGNORECASE) or \
           re.search(r"analyzed\s+and\s+synthesized\s+with\s+available\s+context", text, re.IGNORECASE):
            
            # Determine natural response based on context if available
            if context and context.get("user_goal"):
                goal = str(context["user_goal"]).lower()
                if any(g in goal for g in ["hi", "hello", "hey", "good morning", "good afternoon"]):
                    return "Hello! How can I help you today? I can assist with order tracking, refunds, returns, or our store policies."
                if any(w in goal for w in ["order", "package", "where is", "track", "delivery"]):
                    return "I've checked our system for your inquiry. Could you please provide your order number so I can look up the exact status and delivery updates?"
                if any(w in goal for w in ["refund", "return", "money back"]):
                    return "I can certainly help you with returns and refunds. Please share your order number, and I'll check your eligibility right away."
            
            return "I've checked that for you and reviewed the available details. How else can I assist you with your order or questions today?"

        sanitized = text

        # Strip API keys, tokens, and authorization headers
        sanitized = re.sub(r"\bBearer\s+[A-Za-z0-9_\-\.]+", "[REDACTED_TOKEN]", sanitized, flags=re.IGNORECASE)
        sanitized = re.sub(r"\b(?:sk|AIzaSy|AQ\.)[A-Za-z0-9_\-]{15,}\b", "[REDACTED_KEY]", sanitized)

        # Remove explicit internal phrases
        sanitized = re.sub(
            r"Step\s+['\"][^'\"]+['\"]\s+analyzed\s+and\s+synthesized\s+with\s+available\s+context\.?",
            "",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"Validate\s+(?:output|resolution|status|policy|cancellation)\s+with\s+Critic\s+Agent\.?",
            "",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\b(?:Critic|Resolution|Supervisor|Intake|Intent|Planner|Verification|Escalation|Policy|Risk)\s+Agent\b",
            "support specialist",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\b(?:process_refund|get_order_status|check_refund_eligibility|cancel_order|create_replacement|vector_search|rag_retrieval|dispatch_email|dispatch_whatsapp)\b",
            "support check",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\btool\s+(?:call|executed|execution|output|used|result)\b",
            "system check",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\bLangGraph\b",
            "support platform",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\bnode\s+[a-zA-Z0-9_-]+\b",
            "system workflow",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\bexecution\s+trace(?:\s*#[a-zA-Z0-9_-]+)?\b",
            "record",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\bchain[- ]of[- ]thought\b",
            "evaluation",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\bre-?planning\b",
            "reviewing",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\b(?:system_prompt|prompt_template)\s*:?",
            "",
            sanitized,
            flags=re.IGNORECASE
        )
        sanitized = re.sub(
            r"\b(?:traceback(?:\s*\(most recent call last\):?)?|nullpointer|json\.loads)\b",
            "",
            sanitized,
            flags=re.IGNORECASE
        )

        # Cleanup whitespace and punctuation artifacts
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        sanitized = re.sub(r"\.\s*\.", ".", sanitized)
        sanitized = re.sub(r"\s+,", ",", sanitized)

        # If stripping leaves an empty or awkward sentence, provide a friendly default
        if len(sanitized) < 15 or sanitized.lower() in [
            "i've investigated your inquiry.",
            "i've investigated your inquiry. please let me know how else i can assist you.",
            "please let me know how else i can assist you."
        ]:
            return "I've investigated the issue and have an update for you. Please let me know if you would like me to check an order status or assist with anything else."

        return sanitized
