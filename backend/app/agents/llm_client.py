import os
import json
import re
from pathlib import Path
import httpx
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Auto-load environment variables
_curr_dir = Path(__file__).resolve().parent
load_dotenv(_curr_dir.parent.parent / ".env")
load_dotenv(_curr_dir.parent.parent.parent / ".env")
load_dotenv()

class LLMClient:
    """Universal LLM client with native Google Gemini support, OpenAI-compatible APIs,
    and automatic fallback to deterministic logic."""

    def __init__(self):
        self._refresh_config()

    def _clean_str(self, val: Optional[str]) -> str:
        if not val:
            return ""
        return val.strip().strip('"').strip("'")

    def _refresh_config(self):
        gemini_key = self._clean_str(
            os.getenv("gemini_api_key") or os.getenv("GEMINI_API_KEY")
        )
        provider = self._clean_str(os.getenv("LLM_PROVIDER", "local")).lower()

        # If Gemini key is supplied, auto-upgrade provider to gemini unless specified otherwise
        if gemini_key and provider in ["local", "gemini", ""]:
            provider = "gemini"

        self.provider = provider
        if self.provider == "gemini":
            self.api_key = gemini_key or self._clean_str(os.getenv("LLM_API_KEY", ""))
            self.model = self._clean_str(os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-3.6-flash")
            self.base_url = self._clean_str(os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"))
        else:
            self.api_key = self._clean_str(os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", "")))
            self.model = self._clean_str(os.getenv("LLM_MODEL", "gpt-4o-mini"))
            self.base_url = self._clean_str(os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))

    def is_cloud_enabled(self) -> bool:
        self._refresh_config()
        return bool(self.api_key and self.provider in ["gemini", "openai", "groq", "openrouter"])

    def _build_messages(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        chat_messages: List[Dict[str, str]] = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})

        if messages:
            for m in messages:
                role = m.get("role", "user")
                # Normalize assistant/agent role
                if role in ["assistant", "agent", "bot"]:
                    norm_role = "assistant"
                elif role == "system":
                    norm_role = "system"
                else:
                    norm_role = "user"
                chat_messages.append({"role": norm_role, "content": m.get("content", "")})

        if prompt:
            chat_messages.append({"role": "user", "content": prompt})

        return chat_messages

    def _extract_gemini_text_from_response(self, data: Any) -> Optional[str]:
        """Robustly extracts generated text from Gemini REST generateContent API response.
        Preserves multi-paragraphs, formatting, quotes, and punctuation without regex truncations.
        Handles safety blocks, empty candidates, and malformed structures cleanly.
        """
        if not isinstance(data, dict):
            return None

        # 1. Prompt feedback safety/block inspection
        prompt_feedback = data.get("promptFeedback")
        if isinstance(prompt_feedback, dict):
            block_reason = prompt_feedback.get("blockReason")
            if block_reason:
                print(f"[LLMClient] Prompt blocked by Gemini safety filter: {block_reason}")
                return None

        # 2. Candidate inspection
        candidates = data.get("candidates")
        if not candidates or not isinstance(candidates, list) or len(candidates) == 0:
            return None

        candidate = candidates[0]
        if not isinstance(candidate, dict):
            return None

        # 3. Finish reason verification
        finish_reason = candidate.get("finishReason")
        if finish_reason in ["SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII"]:
            print(f"[LLMClient] Candidate blocked due to safety finishReason: {finish_reason}")
            return None

        content_obj = candidate.get("content")
        if not content_obj or not isinstance(content_obj, dict):
            return None

        parts = content_obj.get("parts")
        if not parts or not isinstance(parts, list):
            return None

        text_segments: List[str] = []
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                t = part.get("text")
                if isinstance(t, str):
                    text_segments.append(t)

        if not text_segments:
            return None

        full_text = "".join(text_segments).strip()
        if not full_text:
            return None

        # Clean thinking/scratchpad blocks if generated by thinking models (<think>...</think>)
        cleaned = re.sub(r"<(?:think|thought)>[\s\S]*?</(?:think|thought)>", "", full_text, flags=re.IGNORECASE).strip()

        # Clean draft labels at the very beginning if model wrote "Draft 1: ..."
        draft_match = re.match(r"^(?:Draft\s*\d+:?\s*|\*Draft\s*\d+:?\*\s*)([\s\S]+)$", cleaned, flags=re.IGNORECASE)
        if draft_match:
            cleaned = draft_match.group(1).strip()

        # If the entire message is wrapped in single or double quotes, strip outer pair
        if len(cleaned) >= 2 and ((cleaned.startswith('"') and cleaned.endswith('"')) or (cleaned.startswith("'") and cleaned.endswith("'"))):
            cleaned = cleaned[1:-1].strip()

        return cleaned if cleaned else None

    def _call_gemini_direct_rest(self, prompt: str, system_prompt: Optional[str] = None, model_name: Optional[str] = None) -> Optional[str]:
        """Call Google Generative Language REST API with bounded timeout and failover."""
        candidate_models = [model_name or self.model, "gemini-2.0-flash", "gemini-1.5-flash"]
        seen = set()
        for m in candidate_models:
            if not m or m in seen:
                continue
            seen.add(m)
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
                combined_prompt = (
                    f"{system_prompt}\n\n"
                    "OUTPUT FORMAT REQUIREMENT: Output ONLY the final response message to the customer. "
                    "Do NOT include internal reasoning, bullet points about persona, or draft labels.\n\n"
                    f"Customer message & context:\n{prompt}"
                ) if system_prompt else prompt
                payload: Dict[str, Any] = {
                    "contents": [{"parts": [{"text": combined_prompt}]}]
                }
                with httpx.Client(timeout=5.0) as client:
                    res = client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        extracted = self._extract_gemini_text_from_response(data)
                        if extracted:
                            return extracted
                    elif res.status_code == 400:
                        try:
                            data = res.json()
                            extracted = self._extract_gemini_text_from_response(data)
                            if extracted:
                                return extracted
                        except Exception:
                            pass
            except Exception as e:
                print(f"[LLMClient direct REST fallback warning for {m}]: {e}")
        return None

    def generate_text(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """Synchronously call LLM to generate natural, conversational text response."""
        if not self.is_cloud_enabled():
            return None

        chat_messages = self._build_messages(prompt, system_prompt, messages)
        if not chat_messages:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
            with httpx.Client(timeout=15.0) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        if content and content.strip():
                            clean_content = re.sub(r"<(?:think|thought)>[\s\S]*?</(?:think|thought)>", "", content, flags=re.IGNORECASE).strip()
                            return clean_content
                elif self.provider == "gemini":
                    # Attempt direct REST multi-model failover (e.g. if primary model hits 429 quota)
                    user_str = prompt or (messages[-1]["content"] if messages else "")
                    direct_res = self._call_gemini_direct_rest(user_str, system_prompt)
                    if direct_res:
                        return direct_res
        except Exception as e:
            print(f"[LLMClient Warning] LLM text generation error: {e}")
            if self.provider == "gemini":
                user_str = prompt or (messages[-1]["content"] if messages else "")
                return self._call_gemini_direct_rest(user_str, system_prompt)

        return None

    async def agenerate_text(
        self,
        prompt: Optional[str] = None,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """Asynchronously call LLM to generate natural, conversational text response."""
        if not self.is_cloud_enabled():
            return None

        chat_messages = self._build_messages(prompt, system_prompt, messages)
        if not chat_messages:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        try:
            endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            print(f"[LLMClient Warning] Async LLM text generation error: {e}")

        # Synchronous fallback if async fails
        return self.generate_text(prompt, system_prompt, messages, temperature, max_tokens)

    async def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> Optional[Dict[str, Any]]:
        """Asynchronously call external LLM and parse JSON response."""
        if not self.is_cloud_enabled():
            return None

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
            "response_format": {"type": "json_object"},
            "temperature": temperature
        }

        try:
            endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
            async with httpx.AsyncClient(timeout=25.0) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    content_clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
                    return json.loads(content_clean)
        except Exception as e:
            print(f"[LLMClient Warning] Async LLM JSON generation error: {e}")

        return None

    agenerate_json = generate_json

    def generate_json_sync(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> Optional[Dict[str, Any]]:
        """Synchronously call LLM and parse JSON response."""
        if not self.is_cloud_enabled():
            return None

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
            "response_format": {"type": "json_object"},
            "temperature": temperature
        }

        try:
            endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
            with httpx.Client(timeout=25.0) as client:
                response = client.post(endpoint, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    content_clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
                    return json.loads(content_clean)
        except Exception as e:
            print(f"[LLMClient Warning] LLM JSON generation error: {e}")

        return None

llm_client = LLMClient()
