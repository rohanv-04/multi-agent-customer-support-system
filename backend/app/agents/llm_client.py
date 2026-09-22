import os
import json
import httpx
from typing import Dict, Any, List, Optional

class LLMClient:
    """Universal LLM client with support for OpenAI-compatible APIs and intelligent local fallback."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "local").lower()
        self.api_key = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")

    def is_cloud_enabled(self) -> bool:
        return bool(self.api_key and self.provider in ["openai", "groq", "openrouter"])

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call external LLM and parse JSON response if API key is provided."""
        if not self.is_cloud_enabled():
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"} if "openai" in self.provider else None,
                    "temperature": 0.2
                }
                response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
        except Exception as e:
            # Fall back gracefully to local agent logic
            print(f"[LLMClient Warning] Cloud LLM error: {e}. Using deterministic agent engine.")
            return None
        return None

llm_client = LLMClient()
