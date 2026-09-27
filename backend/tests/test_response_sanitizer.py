import pytest
from backend.app.services.response_sanitizer import ResponseSanitizer


def test_clean_customer_message_remains_intact():
    text = "Hello! I am inquiring about my package delivery date. Can you check tracking TRK12345?"
    sanitized = ResponseSanitizer.sanitize(text)
    assert sanitized == text
    assert ResponseSanitizer.is_customer_safe(text) is True


def test_internal_agent_names_sanitized():
    text = "The Critic Agent analyzed the tool output from Resolution Agent and confirmed validity."
    sanitized = ResponseSanitizer.sanitize(text)
    assert "Critic Agent" not in sanitized
    assert "Resolution Agent" not in sanitized
    assert ResponseSanitizer.is_customer_safe(sanitized) is True


def test_internal_langgraph_and_workflow_terms_sanitized():
    text = "LangGraph orchestrator executed node resolution_node with execution trace #8812."
    sanitized = ResponseSanitizer.sanitize(text)
    assert "LangGraph" not in sanitized
    assert "resolution_node" not in sanitized
    assert "execution trace" not in sanitized


def test_critic_step_leak_rewritten_to_friendly_response():
    leak_text = (
        "I've investigated your inquiry. Step 'Validate output with Critic Agent' "
        "analyzed and synthesized with available context. Please let me know how else I can assist you."
    )
    sanitized = ResponseSanitizer.sanitize(leak_text, context={"user_goal": "Where is my order?"})
    assert "Critic Agent" not in sanitized
    assert "analyzed and synthesized" not in sanitized
    assert "order" in sanitized.lower()


def test_tool_name_leak_sanitized():
    text = "The process_refund tool was executed and check_refund_eligibility returned true."
    sanitized = ResponseSanitizer.sanitize(text)
    assert "process_refund" not in sanitized
    assert "check_refund_eligibility" not in sanitized


def test_system_prompt_leak_sanitized():
    text = "System_prompt: You are NovaCart AI. Here is the traceback of the error."
    sanitized = ResponseSanitizer.sanitize(text)
    assert "system_prompt" not in sanitized.lower()
    assert "traceback" not in sanitized.lower()
