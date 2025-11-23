# agent/chat_agent.py
"""
ChatAgent: answers user questions using the existing account plan as context.
It uses Google Gemini (google-genai) to produce a concise, helpful answer.
"""

import logging
import json
import re
from typing import Dict, Any

from google import genai
from config import GEMINI_API_KEY, GEMINI_TEXT_MODEL

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_genai_client = genai.Client(api_key=GEMINI_API_KEY)


class ChatAgent:
    def __init__(self, model: str = GEMINI_TEXT_MODEL):
        self.client = _genai_client
        self.model = model

    def _call_gemini(self, prompt: str) -> str:
        try:
            resp = self.client.models.generate_content(model=self.model, contents=prompt)
        except Exception as e:
            logger.exception("Gemini primary call failed: %s", e)
            try:
                resp = self.client.generate(model=self.model, prompt=prompt)
            except Exception as e2:
                logger.exception("Gemini fallback failed: %s", e2)
                raise RuntimeError(f"Gemini call failed: {e} / {e2}")

        # Defensive extraction
        text_output = ""
        if hasattr(resp, "text") and resp.text:
            text_output = resp.text
        elif hasattr(resp, "output"):
            try:
                out = resp.output
                first = out[0] if isinstance(out, (list, tuple)) and out else out
                if isinstance(first, dict):
                    content = first.get("content") or first.get("contents")
                    if isinstance(content, list) and content:
                        for c in content:
                            if isinstance(c, dict) and "text" in c and c["text"]:
                                text_output = c["text"]
                                break
                    elif isinstance(content, str):
                        text_output = content
                elif isinstance(first, str):
                    text_output = first
            except Exception:
                text_output = ""
        else:
            try:
                text_output = str(resp)
            except Exception:
                text_output = ""

        return (text_output or "").strip()

    def answer(self, question: str, plan: Dict[str, Any]) -> str:
        """
        Produces an answer to `question` using `plan` as context.
        The model is explicitly instructed NOT to modify the plan, only to reference it.
        """
        # Build a compact context: include sections with labels and sources
        # but limit the amount so we don't exceed token caps.
        def excerpt(s):
            if not s:
                return ""
            s = str(s).strip()
            return s if len(s) <= 1200 else s[:1200] + " ..."

        context_lines = []
        # Use key plan fields as context
        keys = ["company_overview", "key_findings", "pain_points", "opportunities", "competitors", "recommended_strategy"]
        for k in keys:
            val = plan.get(k, "")
            if val:
                context_lines.append(f"{k}:\n{excerpt(val)}\n")

        # Sources (short list)
        sources = plan.get("sources", []) or []
        if sources:
            sources_excerpt = "\n".join([str(s) for s in sources[:6]])
            context_lines.append(f"sources (first 6):\n{sources_excerpt}\n")

        context_text = "\n\n".join(context_lines)

        prompt = f"""
You are a helpful, concise business research assistant.

CONTEXT: Here is the account plan (do not change it). Use it to answer the user's question. If the plan does not contain enough info to answer, say you don't know and suggest what extra info you need or which external sources to check. Do NOT invent facts. If you cite something, indicate whether it comes from the plan or say 'outside plan — needs web check'.

Account plan context (shortened):
{context_text}

QUESTION:
{question}

REQUIREMENTS:
- Answer concisely (2-6 sentences) unless user asks for details.
- If you are uncertain, say so and list 1-3 next steps for the user to verify the claim.
- Indicate any plan section you referenced in square brackets, e.g. [Pain Points].
- Output plain text only.
"""

        logger.info("ChatAgent answering question (truncated prompt)...")
        raw = self._call_gemini(prompt)

        # If the model returns a JSON wrapper or other noise, prefer the first paragraph
        if not raw:
            return "I couldn't generate an answer. Try rephrasing the question or ask for a specific section of the plan."

        # Clean up text (strip leading/trailing markers)
        # If model returns multiple lines, keep them as-is
        return raw.strip()
