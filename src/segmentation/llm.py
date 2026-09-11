from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


SYSTEM_PROMPT = """You are indexing a legal deposition into chronological topics.
You receive numbered transcript CHUNKS. Each chunk already has immutable CHUNK_ID and SOURCE_RANGE.
You MUST NOT invent page numbers, line numbers, or source ranges.
You only reason about topic identity and transitions.

Return JSON only:
{
  "decisions": [
    {
      "chunk_id": "C001",
      "action": "new_topic" | "continue" | "brief_digression" | "return_to_previous" | "related_distinct" | "overlapping",
      "topic_label": "short attorney-useful topic name",
      "confidence": 0.0,
      "notes": "one sentence"
    }
  ]
}

Rules:
- Do not make every question a separate topic.
- Do not create enormous topics covering unrelated testimony.
- Objections, reporter/videographer remarks, and breaks are digressions, not new substantive topics.
- If the same subject returns much later, use related_distinct or return_to_previous, not continue.
"""


def llm_available() -> bool:
    provider = os.getenv("DEPOINDEX_LLM_PROVIDER", "none").strip().lower()
    if provider in ("", "none"):
        return False
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    if provider == "ollama":
        return True
    return False


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def complete_json(user_content: str) -> dict | None:
    provider = os.getenv("DEPOINDEX_LLM_PROVIDER", "none").strip().lower()
    temperature = float(os.getenv("DEPOINDEX_TEMPERATURE", "0"))
    try:
        if provider == "openai" and os.getenv("OPENAI_API_KEY"):
            base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            payload = {
                "model": model,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
            }
            out = _post_json(f"{base}/chat/completions", payload, headers)
            content = out["choices"][0]["message"]["content"]
            return json.loads(content)
        if provider == "ollama":
            host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
            model = os.getenv("OLLAMA_MODEL", "llama3.1")
            payload = {
                "model": model,
                "stream": False,
                "format": "json",
                "options": {"temperature": temperature},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
            }
            out = _post_json(f"{host}/api/chat", payload, {"Content-Type": "application/json"})
            content = out.get("message", {}).get("content", "{}")
            return json.loads(content)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError):
        return None
    return None
