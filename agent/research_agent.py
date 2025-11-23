# agent/research_agent.py
"""
ResearchAgent: performs web search via Tavily and synthesizes an account plan
using Google Gemini (google-genai). This version asks Gemini for much more
elaborated content and will automatically re-ask to expand short sections.
"""

import json
import re
import logging
from typing import Tuple, List, Dict, Any

from tavily import TavilyClient
from google import genai

from agent.account_plan_template import ACCOUNT_PLAN_TEMPLATE
from config import TAVILY_API_KEY, GEMINI_API_KEY, GEMINI_TEXT_MODEL

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize clients once
_tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
_genai_client = genai.Client(api_key=GEMINI_API_KEY)


class ResearchAgent:
    def __init__(self, text_model: str = GEMINI_TEXT_MODEL):
        self.tavily = _tavily_client
        self.client = _genai_client
        self.text_model = text_model

    def search_company(self, company_name: str, top_k: int = 8) -> Tuple[str, List[str]]:
        """
        Perform a Tavily search for the given company name.
        Returns combined_text (concatenated snippets) and a list of source URLs.
        """
        query = f"{company_name} company overview business model latest news competitors funding"
        logger.info("Running Tavily search for query: %s", query)

        try:
            raw = self.tavily.search(query=query, limit=top_k, include_raw_content=True)
        except Exception as e:
            logger.exception("Tavily search failed: %s", e)
            return "", []

        combined_text = ""
        sources: List[str] = []

        # Normalize result shapes
        results = []
        if isinstance(raw, dict):
            results = raw.get("results") or raw.get("hits") or raw.get("items") or []
        elif isinstance(raw, list):
            results = raw
        else:
            try:
                results = list(raw)
            except Exception:
                results = []

        for r in results[:top_k]:
            if not r:
                continue
            content = None
            for k in ("content", "snippet", "text", "summary"):
                if isinstance(r, dict) and k in r and r[k]:
                    content = r[k]
                    break
            if content is None and isinstance(r, str):
                content = r
            if content:
                combined_text += content + "\n\n"

            url = None
            if isinstance(r, dict):
                for k in ("url", "link", "source", "href"):
                    if k in r and r[k]:
                        url = r[k]
                        break
            if url:
                sources.append(url)

        # dedupe sources
        seen = set()
        deduped_sources = []
        for s in sources:
            if s not in seen:
                deduped_sources.append(s)
                seen.add(s)

        logger.info("Tavily search collected %d chars and %d sources", len(combined_text), len(deduped_sources))
        return combined_text.strip(), deduped_sources

    def _call_gemini(self, prompt: str) -> str:
        """
        Call Gemini via genai client; defensive extraction of text.
        """
        try:
            resp = self.client.models.generate_content(model=self.text_model, contents=prompt)
        except Exception as e:
            logger.exception("Primary genai.models.generate_content failed: %s", e)
            try:
                resp = self.client.generate(model=self.text_model, prompt=prompt)
            except Exception as e2:
                logger.exception("Fallback genai.generate failed: %s", e2)
                raise RuntimeError(f"Gemini invocation failed: {e} / {e2}")

        text_output = ""
        # Try common shapes
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

        logger.debug("Gemini raw output length: %d", len(text_output or ""))
        return (text_output or "").strip()

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """
        Attempts to find and parse the first JSON object in text.
        """
        if not text:
            return {}
        m = re.search(r"(\{.*\})", text, flags=re.DOTALL)
        if m:
            json_str = m.group(1)
            try:
                return json.loads(json_str)
            except Exception:
                # try lenient cleanup
                try:
                    cleaned = re.sub(r",\s*}", "}", json_str)
                    cleaned = re.sub(r",\s*\]", "]", cleaned)
                    return json.loads(cleaned)
                except Exception:
                    return {}
        return {}

    def _ensure_long_sections(self, plan: Dict[str, Any], research_data: str, company_name: str) -> Dict[str, Any]:
        """
        If any key in plan is too short (< threshold), ask Gemini to expand those keys
        and merge expanded text into the plan.
        """
        MIN_CHARS = 300  # threshold: below this, we expand
        keys_to_expand = [k for k in ACCOUNT_PLAN_TEMPLATE.keys() if len(str(plan.get(k, "") or "")) < MIN_CHARS]
        if not keys_to_expand:
            return plan

        logger.info("Expanding short sections: %s", keys_to_expand)
        # Build an expand prompt asking only for the specific keys as long text
        keys_list = ", ".join(keys_to_expand)
        expand_prompt = f"""
You are an expert enterprise sales analyst. Expand the following sections into much more detailed content.
Company: {company_name}

Sections to expand: {keys_list}

For each requested section, produce a long, well-structured plain-text value (not bullet fragments) of about 150-400 words each, using the research provided. Output ONLY valid JSON with keys exactly matching the section names and values as strings.

Research context (use for evidence):
{research_data}
"""
        expanded_text = self._call_gemini(expand_prompt)
        expanded_obj = self._extract_json_from_text(expanded_text)

        # Merge expanded_obj into plan for keys present
        for k in keys_to_expand:
            val = expanded_obj.get(k)
            if val and isinstance(val, str) and len(val.strip()) > len(str(plan.get(k, "") or "")):
                plan[k] = val.strip()
        return plan

    def generate_account_plan(self, research_data: str, sources: List[str], company_name: str) -> Dict[str, Any]:
        """
        Create a structured account plan from research_data asking for elaborated content.
        Steps:
          1) Ask Gemini to output JSON with detailed multi-paragraph values (~150-400 words each).
          2) If any section is still short, call Gemini again to expand those sections and merge.
        """
        prompt = f"""
You are an expert enterprise sales analyst. Parse the following research text and produce a JSON object
with these keys (exact): company_overview, key_findings, pain_points, opportunities, competitors, recommended_strategy

For EACH key produce a detailed, multi-paragraph, well-written section (aim for ~150-400 words per section).
Use evidence from the research. Where helpful, include brief inline citations in parentheses (e.g., 'According to [source]...').

Important:
- Output ONLY valid JSON (no explanatory text). Each value must be a plain string (you may include newlines).
- Keep JSON parsable (avoid trailing commas).

Company: {company_name}

Research:
{research_data}
"""
        logger.info("Calling Gemini to synthesize detailed account plan for %s", company_name)
        text_output = self._call_gemini(prompt)

        parsed_obj = self._extract_json_from_text(text_output)

        if not isinstance(parsed_obj, dict) or not any(parsed_obj.values()):
            # fallback: put raw model text into company_overview (but ideally won't happen)
            logger.warning("Gemini did not return valid JSON. Falling back to raw text.")
            parsed_obj = {
                "company_overview": (text_output or "").strip(),
                "key_findings": "",
                "pain_points": "",
                "opportunities": "",
                "competitors": "",
                "recommended_strategy": ""
            }

        # Ensure all required keys exist
        plan = {}
        for k in ACCOUNT_PLAN_TEMPLATE.keys():
            plan[k] = str(parsed_obj.get(k, "")).strip() if parsed_obj.get(k, "") is not None else ""

        # If any section is still short, request expansion and merge
        plan = self._ensure_long_sections(plan, research_data, company_name)

        # Attach sources and confidence estimate
        plan["sources"] = sources or []
        plan["confidence_estimate"] = f"{min(95, 20 + 10 * len(plan['sources']))}%"

        logger.info("Generated detailed account plan with keys: %s", list(plan.keys()))
        return plan
