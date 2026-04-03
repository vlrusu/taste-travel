from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AISeedExtractionService:
    TAXONOMY = {
        "vibe": ["lively", "calm", "romantic", "energetic", "stylish", "grounded", "warm", "neighborhood", "local", "buzzy", "unpretentious"],
        "formality": ["casual", "casual_polished", "polished", "formal"],
        "food_style": ["strong_food_identity", "creative", "classic", "comfort_food", "chef_driven", "experimental", "traditional"],
        "social_feel": ["neighborhood_favorite", "destination", "tourist_heavy", "local_leaning"],
        "use_case": ["date_night", "groups", "everyday", "special_occasion", "late_night"],
        "cuisine_style": ["small_plates", "seafood", "tapas", "bistro", "tasting_menu", "regional", "wine_bar", "cafe", "bakery"],
    }

    EMPTY_RESULT = {
        "vibe": [],
        "formality": None,
        "food_style": [],
        "social_feel": [],
        "use_case": [],
        "cuisine_style": [],
        "confidence": 0.0,
        "reasoning_summary": "",
    }

    def __init__(self) -> None:
        self.settings = get_settings()

    @staticmethod
    def _extract_output_text(payload: dict[str, Any]) -> str | None:
        direct_output = payload.get("output_text")
        if isinstance(direct_output, str) and direct_output.strip():
            return direct_output

        output_items = payload.get("output")
        if not isinstance(output_items, list):
            return None

        text_chunks: list[str] = []
        for item in output_items:
            if not isinstance(item, dict):
                continue
            contents = item.get("content")
            if not isinstance(contents, list):
                continue
            for content in contents:
                if not isinstance(content, dict):
                    continue
                content_type = str(content.get("type") or "")
                if content_type not in {"output_text", "text"}:
                    continue
                text_value = content.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    text_chunks.append(text_value)
                elif isinstance(text_value, dict):
                    value = text_value.get("value")
                    if isinstance(value, str) and value.strip():
                        text_chunks.append(value)

        if not text_chunks:
            return None

        return "\n".join(text_chunks)

    def extract_traits(
        self,
        *,
        seed_name: str,
        city: str,
        raw_seed_note_text: str | None,
        raw_place_metadata_json: dict[str, Any] | None,
        raw_review_text: str | None,
        editorial_summary_text: str | None,
        menu_summary_text: str | None,
    ) -> dict[str, Any] | None:
        if not self.settings.openai_api_key:
            logger.debug("AI seed extraction skipped for %s in %s because OPENAI_API_KEY is not configured", seed_name, city)
            return None

        prompt = {
            "restaurant_name": seed_name,
            "city": city,
            "raw_seed_note_text": raw_seed_note_text,
            "raw_place_metadata_json": raw_place_metadata_json,
            "raw_review_text": raw_review_text,
            "editorial_summary_text": editorial_summary_text,
            "menu_summary_text": menu_summary_text,
            "taxonomy": self.TAXONOMY,
            "instructions": (
                "Extract only supported taxonomy values. Return compact JSON only. "
                "Use null for formality if unclear. Confidence must be 0 to 1."
            ),
        }

        try:
            logger.debug("Attempting AI seed extraction for %s in %s with model=%s", seed_name, city, self.settings.openai_model)
            response = httpx.post(
                f"{self.settings.openai_base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.settings.openai_model,
                    "input": [
                        {
                            "role": "system",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": (
                                        "You extract restaurant traits into a fixed taxonomy. "
                                        "Return valid JSON with exactly these keys: "
                                        "vibe, formality, food_style, social_feel, use_case, cuisine_style, confidence, reasoning_summary."
                                    ),
                                }
                            ],
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": json.dumps(prompt),
                                }
                            ],
                        },
                    ],
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "seed_traits",
                            "schema": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "vibe": {"type": "array", "items": {"type": "string", "enum": self.TAXONOMY["vibe"]}},
                                    "formality": {"anyOf": [{"type": "string", "enum": self.TAXONOMY["formality"]}, {"type": "null"}]},
                                    "food_style": {"type": "array", "items": {"type": "string", "enum": self.TAXONOMY["food_style"]}},
                                    "social_feel": {"type": "array", "items": {"type": "string", "enum": self.TAXONOMY["social_feel"]}},
                                    "use_case": {"type": "array", "items": {"type": "string", "enum": self.TAXONOMY["use_case"]}},
                                    "cuisine_style": {"type": "array", "items": {"type": "string", "enum": self.TAXONOMY["cuisine_style"]}},
                                    "confidence": {"type": "number"},
                                    "reasoning_summary": {"type": "string"},
                                },
                                "required": [
                                    "vibe",
                                    "formality",
                                    "food_style",
                                    "social_feel",
                                    "use_case",
                                    "cuisine_style",
                                    "confidence",
                                    "reasoning_summary",
                                ],
                            },
                        }
                    },
                },
                timeout=self.settings.openai_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            raw_output = self._extract_output_text(payload)
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "AI seed extraction failed for %s in %s with status=%s response=%s",
                seed_name,
                city,
                exc.response.status_code,
                exc.response.text[:500],
            )
            return None
        except httpx.HTTPError as exc:
            logger.warning("AI seed extraction transport error for %s in %s: %s", seed_name, city, exc)
            return None
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("AI seed extraction response parsing failed for %s in %s: %s", seed_name, city, exc)
            return None

        if not raw_output:
            logger.warning("AI seed extraction returned no output_text for %s in %s", seed_name, city)
            return None

        try:
            parsed = json.loads(raw_output)
        except (TypeError, json.JSONDecodeError):
            logger.warning("AI seed extraction returned invalid JSON for %s in %s", seed_name, city)
            return None

        logger.debug("AI seed extraction succeeded for %s in %s", seed_name, city)
        return self._sanitize(parsed)

    @classmethod
    def _sanitize(cls, parsed: dict[str, Any]) -> dict[str, Any]:
        result = dict(cls.EMPTY_RESULT)
        for key in ["vibe", "food_style", "social_feel", "use_case", "cuisine_style"]:
            values = parsed.get(key, [])
            allowed = set(cls.TAXONOMY[key])
            result[key] = [value for value in values if value in allowed]
        formality = parsed.get("formality")
        result["formality"] = formality if formality in cls.TAXONOMY["formality"] else None
        try:
            confidence = float(parsed.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        result["confidence"] = max(0.0, min(confidence, 1.0))
        result["reasoning_summary"] = str(parsed.get("reasoning_summary", ""))[:300]
        return result
