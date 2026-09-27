import pytest
from unittest.mock import patch, MagicMock
from backend.app.agents.llm_client import LLMClient


@pytest.fixture
def client():
    return LLMClient()


def test_1_normal_single_paragraph_response(client):
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Your order ORD10001 is on schedule and will arrive by tomorrow."}]
                },
                "finishReason": "STOP"
            }
        ]
    }
    extracted = client._extract_gemini_text_from_response(data)
    assert extracted == "Your order ORD10001 is on schedule and will arrive by tomorrow."


def test_2_multi_paragraph_response(client):
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                "Hello Kavin,\n\n"
                                "Thank you for reaching out to NovaCart support.\n\n"
                                "Your package with tracking number TRK99281 has shipped via FedEx.\n"
                                "Estimated delivery is October 2nd."
                            )
                        }
                    ]
                },
                "finishReason": "STOP"
            }
        ]
    }
    extracted = client._extract_gemini_text_from_response(data)
    assert "\n\n" in extracted
    assert "TRK99281" in extracted
    assert "Estimated delivery is October 2nd." in extracted


def test_3_response_containing_quoted_text(client):
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": 'Your item "Apple iPad Pro 11-inch M4" has been marked as "Delivered" at your front door.'
                        }
                    ]
                },
                "finishReason": "STOP"
            }
        ]
    }
    extracted = client._extract_gemini_text_from_response(data)
    assert 'Your item "Apple iPad Pro 11-inch M4"' in extracted
    assert '"Delivered"' in extracted
    # Ensure it didn't strip everything except the quote
    assert extracted.startswith("Your item")


def test_4_response_containing_please_choose_an_option(client):
    # Tests that prompt instructions like 'Please choose an option' don't get truncated
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                "I have checked your account. We never say 'Please choose an option' robotically. "
                                "Instead, I can directly refund your delayed order ORD10002 or issue store credit."
                            )
                        }
                    ]
                },
                "finishReason": "STOP"
            }
        ]
    }
    extracted = client._extract_gemini_text_from_response(data)
    assert extracted is not None
    assert "ORD10002" in extracted
    assert "Please choose an option" in extracted
    assert extracted != "Please choose an option"


def test_5_autonomous_refund_response(client):
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                "I completely understand your frustration regarding order ORD10002.\n\n"
                                "I have approved and processed a full refund of $499.00 USD to your original card.\n"
                                "Your transaction confirmation reference is REF-ORD10002-8821. "
                                "The funds will appear in 3-5 business days."
                            )
                        }
                    ]
                },
                "finishReason": "STOP"
            }
        ]
    }
    extracted = client._extract_gemini_text_from_response(data)
    assert "refund" in extracted.lower()
    assert "$499.00" in extracted
    assert "REF-ORD10002-8821" in extracted
    assert "\n\n" in extracted


def test_6_empty_model_response(client):
    data = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "   "}]
                },
                "finishReason": "STOP"
            }
        ]
    }
    extracted = client._extract_gemini_text_from_response(data)
    assert extracted is None


def test_7_malformed_response(client):
    assert client._extract_gemini_text_from_response(None) is None
    assert client._extract_gemini_text_from_response({}) is None
    assert client._extract_gemini_text_from_response({"candidates": []}) is None
    assert client._extract_gemini_text_from_response({"candidates": [{}]}) is None
    assert client._extract_gemini_text_from_response({"candidates": [{"content": {}}]}) is None
    assert client._extract_gemini_text_from_response({"candidates": [{"content": {"parts": []}}]}) is None
    assert client._extract_gemini_text_from_response("raw string instead of dict") is None


def test_8_api_error_handling(client):
    # Simulated 500 error from API returns None safely without raising an unhandled exception
    with patch("httpx.Client.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_post.return_value = mock_response

        # Calling generate_text with error should fallback safely to None
        res = client.generate_text(prompt="Hello", system_prompt="Test")
        # In cloud enabled or not, it should not crash
        assert res is None or isinstance(res, str)


def test_9_safety_blocked_response(client):
    # Test finishReason = SAFETY
    safety_data = {
        "candidates": [
            {
                "content": {"parts": [{"text": "Toxic or unsafe content"}]},
                "finishReason": "SAFETY"
            }
        ]
    }
    assert client._extract_gemini_text_from_response(safety_data) is None

    # Test promptFeedback blockReason = SAFETY
    prompt_block_data = {
        "promptFeedback": {"blockReason": "SAFETY"},
        "candidates": []
    }
    assert client._extract_gemini_text_from_response(prompt_block_data) is None
