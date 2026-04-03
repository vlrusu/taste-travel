from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any

from app.services.ai_seed_extraction import AISeedExtractionService
from app.services.restaurant_identity import infer_restaurant_identity

logger = logging.getLogger(__name__)


class SeedEnrichmentService:
    TEXT_RULES: dict[str, dict[str, list[str]]] = {
        "lively": {"vibe": ["lively", "buzzy"], "use_case": ["groups"]},
        "buzzy": {"vibe": ["buzzy", "energetic"], "use_case": ["groups"]},
        "energetic": {"vibe": ["energetic", "lively"]},
        "calm": {"vibe": ["calm"]},
        "romantic": {"vibe": ["romantic"], "use_case": ["date_night"]},
        "stylish": {"vibe": ["stylish"], "formality": ["casual_polished"]},
        "warm": {"vibe": ["warm"]},
        "grounded": {"vibe": ["grounded", "local"]},
        "neighborhood": {"vibe": ["neighborhood", "local"], "social_feel": ["neighborhood_favorite"]},
        "local": {"vibe": ["local"], "social_feel": ["local_leaning"]},
        "date night": {"use_case": ["date_night", "special_occasion"]},
        "special occasion": {"use_case": ["special_occasion"]},
        "late night": {"use_case": ["late_night"]},
        "groups": {"use_case": ["groups"]},
        "everyday": {"use_case": ["everyday"]},
        "creative": {"food_style": ["creative"]},
        "chef driven": {"food_style": ["chef_driven"]},
        "chef-driven": {"food_style": ["chef_driven"]},
        "experimental": {"food_style": ["experimental"]},
        "traditional": {"food_style": ["traditional"]},
        "classic": {"food_style": ["classic"]},
        "comfort": {"food_style": ["comfort_food"]},
        "small plates": {"cuisine_style": ["small_plates"]},
        "tapas": {"cuisine_style": ["tapas", "small_plates"]},
        "bistro": {"cuisine_style": ["bistro"]},
        "seafood": {"cuisine_style": ["seafood"]},
        "regional": {"cuisine_style": ["regional"]},
        "wine bar": {"cuisine_style": ["wine_bar"]},
        "cafe": {"cuisine_style": ["cafe"]},
        "bakery": {"cuisine_style": ["bakery"]},
        "tasting menu": {"cuisine_style": ["tasting_menu"], "formality": ["formal"], "use_case": ["special_occasion"]},
        "touristy": {"social_feel": ["tourist_heavy"]},
        "destination": {"social_feel": ["destination"]},
    }

    EMPTY_TRAITS = {
        "vibe": [],
        "formality": [],
        "food_style": [],
        "social_feel": [],
        "use_case": [],
        "cuisine_style": [],
        "positive_traits": [],
        "negative_traits": [],
    }

    @classmethod
    def _append_unique(cls, target: list[str], values: list[str]) -> None:
        for value in values:
            if value not in target:
                target.append(value)

    @classmethod
    def _apply_text_rules(cls, text: str | None, target: dict[str, list[str]]) -> None:
        if not text:
            return
        lowered = text.lower()
        for phrase, mapping in cls.TEXT_RULES.items():
            if phrase in lowered:
                for category, values in mapping.items():
                    cls._append_unique(target[category], values)

    @classmethod
    def _metadata_traits(
        cls,
        *,
        price_level: str | None,
        rating: float | None,
        user_ratings_total: int | None,
        raw_types: list[str] | None,
    ) -> dict[str, list[str]]:
        traits = {key: [] for key in cls.EMPTY_TRAITS}
        types = set(raw_types or [])
        review_count = user_ratings_total or 0
        review_rating = rating or 0.0

        if "bar" in types:
            cls._append_unique(traits["cuisine_style"], ["wine_bar"])
            cls._append_unique(traits["use_case"], ["groups", "late_night"])
            cls._append_unique(traits["vibe"], ["lively"])
        if "seafood_restaurant" in types:
            cls._append_unique(traits["cuisine_style"], ["seafood"])
            cls._append_unique(traits["food_style"], ["strong_food_identity"])
        if "cafe" in types:
            cls._append_unique(traits["cuisine_style"], ["cafe"])
            cls._append_unique(traits["formality"], ["casual"])
            cls._append_unique(traits["use_case"], ["everyday"])
        if "bakery" in types:
            cls._append_unique(traits["cuisine_style"], ["bakery"])
            cls._append_unique(traits["formality"], ["casual"])
            cls._append_unique(traits["use_case"], ["everyday"])
        if "restaurant" in types:
            cls._append_unique(traits["food_style"], ["strong_food_identity"])

        if price_level in {"$", "$$"}:
            cls._append_unique(traits["formality"], ["casual"])
            cls._append_unique(traits["use_case"], ["everyday"])
        elif price_level == "$$$":
            cls._append_unique(traits["formality"], ["casual_polished"])
            cls._append_unique(traits["use_case"], ["date_night"])
        elif price_level == "$$$$":
            cls._append_unique(traits["formality"], ["formal"])
            cls._append_unique(traits["use_case"], ["special_occasion"])

        if review_rating >= 4.5 and review_count >= 80:
            cls._append_unique(traits["vibe"], ["warm"])
            cls._append_unique(traits["social_feel"], ["local_leaning", "neighborhood_favorite"])
        elif review_count >= 250 and review_rating < 4.4:
            cls._append_unique(traits["social_feel"], ["destination", "tourist_heavy"])
        elif review_count >= 60:
            cls._append_unique(traits["social_feel"], ["local_leaning"])

        if review_count >= 120:
            cls._append_unique(traits["vibe"], ["buzzy"])

        return traits

    @classmethod
    def derive_traits(
        cls,
        *,
        price_level: str | None,
        rating: float | None,
        user_ratings_total: int | None,
        raw_types: list[str] | None,
        review_summary_text: str | None,
        editorial_summary_text: str | None,
        menu_summary_text: str | None,
        seed_notes: str | None,
    ) -> dict[str, list[str]]:
        traits = cls._metadata_traits(
            price_level=price_level,
            rating=rating,
            user_ratings_total=user_ratings_total,
            raw_types=raw_types,
        )
        for text in [review_summary_text, editorial_summary_text, menu_summary_text, seed_notes]:
            cls._apply_text_rules(text, traits)
        identity = infer_restaurant_identity(
            name=str(((seed_notes or "")[:80]) or ((menu_summary_text or "")[:80]) or "seed"),
            raw_types=raw_types,
            cuisine_tags=[value.replace("_", "-") for value in traits["cuisine_style"]],
            vibe_tags=[value.replace("_", "-") for value in traits["vibe"]],
            food_style_tags=traits["food_style"],
            price_level=price_level,
            formality_score=0.8 if "formal" in traits["formality"] else 0.5 if "casual_polished" in traits["formality"] else 0.22,
            tourist_profile="local-leaning" if "local_leaning" in traits["social_feel"] else "destination" if "destination" in traits["social_feel"] or "tourist_heavy" in traits["social_feel"] else "mixed",
            rating=rating,
            user_ratings_total=user_ratings_total,
            text_blobs=[review_summary_text, editorial_summary_text, menu_summary_text, seed_notes],
        )
        traits["positive_traits"] = list(identity["positive_traits"])
        traits["negative_traits"] = list(identity["negative_traits"])
        traits["primary_archetype"] = identity["primary_archetype"]
        traits["secondary_archetypes"] = identity["secondary_archetypes"]
        traits["confidence_score"] = identity["confidence_score"]
        return traits

    @classmethod
    def _merge_ai_traits(cls, base_traits: dict[str, list[str]], ai_traits: dict[str, Any] | None) -> dict[str, list[str]]:
        merged = {key: list(base_traits[key]) for key in cls.EMPTY_TRAITS}
        if "primary_archetype" in base_traits:
            merged["primary_archetype"] = base_traits["primary_archetype"]
        if "secondary_archetypes" in base_traits:
            merged["secondary_archetypes"] = list(base_traits["secondary_archetypes"])
        if "confidence_score" in base_traits:
            merged["confidence_score"] = base_traits["confidence_score"]
        if not ai_traits:
            return merged
        for key in ["vibe", "food_style", "social_feel", "use_case", "cuisine_style", "positive_traits", "negative_traits"]:
            cls._append_unique(merged[key], [str(value) for value in ai_traits.get(key, [])])
        formality = ai_traits.get("formality")
        if isinstance(formality, str):
            cls._append_unique(merged["formality"], [formality])
        return merged

    @classmethod
    def _merge_existing_traits(cls, base_traits: dict[str, list[str]], existing_traits: dict[str, Any] | None) -> dict[str, list[str]]:
        merged = {key: list(base_traits[key]) for key in cls.EMPTY_TRAITS}
        if "primary_archetype" in base_traits:
            merged["primary_archetype"] = base_traits["primary_archetype"]
        if "secondary_archetypes" in base_traits:
            merged["secondary_archetypes"] = list(base_traits["secondary_archetypes"])
        if "confidence_score" in base_traits:
            merged["confidence_score"] = base_traits["confidence_score"]
        if not existing_traits:
            return merged
        for key in ["vibe", "formality", "food_style", "social_feel", "use_case", "cuisine_style", "positive_traits", "negative_traits"]:
            values = existing_traits.get(key, [])
            if isinstance(values, list):
                cls._append_unique(merged[key], [str(value) for value in values])
        if existing_traits.get("primary_archetype") and not merged.get("primary_archetype"):
            merged["primary_archetype"] = str(existing_traits["primary_archetype"])
        if isinstance(existing_traits.get("secondary_archetypes"), list):
            merged["secondary_archetypes"] = list(existing_traits["secondary_archetypes"])
        if existing_traits.get("confidence_score") is not None:
            merged["confidence_score"] = existing_traits["confidence_score"]
        return merged

    @classmethod
    def enrich_seed_payload(
        cls,
        *,
        source: str | None,
        is_verified_place: bool,
        price_level: str | None,
        rating: float | None,
        user_ratings_total: int | None,
        raw_types: list[str] | None,
        review_summary_text: str | None,
        editorial_summary_text: str | None,
        menu_summary_text: str | None,
        seed_notes: str | None,
        raw_seed_note_text: str | None = None,
        raw_place_metadata_json: dict[str, Any] | None = None,
        raw_review_text: str | None = None,
        derived_traits_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not is_verified_place or source != "google_places":
            return {
                "raw_seed_note_text": raw_seed_note_text or seed_notes,
                "raw_place_metadata_json": raw_place_metadata_json,
                "raw_review_text": raw_review_text or review_summary_text,
                "derived_traits_json": derived_traits_json,
                "ai_summary_text": None,
                "enrichment_status": "manual",
                "enriched_at": None,
            }

        deterministic_traits = cls.derive_traits(
            price_level=price_level,
            rating=rating,
            user_ratings_total=user_ratings_total,
            raw_types=raw_types,
            review_summary_text=review_summary_text,
            editorial_summary_text=editorial_summary_text,
            menu_summary_text=menu_summary_text,
            seed_notes=seed_notes,
        )
        ai_result = AISeedExtractionService().extract_traits(
            seed_name=str((raw_place_metadata_json or {}).get("name") or ""),
            city=str((raw_place_metadata_json or {}).get("city") or ""),
            raw_seed_note_text=raw_seed_note_text or seed_notes,
            raw_place_metadata_json=raw_place_metadata_json,
            raw_review_text=raw_review_text or review_summary_text,
            editorial_summary_text=editorial_summary_text,
            menu_summary_text=menu_summary_text,
        )
        merged_traits = cls._merge_existing_traits(deterministic_traits, derived_traits_json)
        merged_traits = cls._merge_ai_traits(merged_traits, ai_result)
        if ai_result:
            enrichment_status = "ai_completed"
        else:
            enrichment_status = "deterministic_only"
        logger.debug(
            "Seed enrichment finished for source=%s verified=%s status=%s has_precomputed_traits=%s has_ai_summary=%s",
            source,
            is_verified_place,
            enrichment_status,
            derived_traits_json is not None,
            bool(ai_result and ai_result.get("reasoning_summary")),
        )
        return {
            "raw_seed_note_text": raw_seed_note_text or seed_notes,
            "raw_place_metadata_json": raw_place_metadata_json,
            "raw_review_text": raw_review_text or review_summary_text,
            "derived_traits_json": merged_traits,
            "ai_summary_text": ai_result.get("reasoning_summary") if ai_result else None,
            "enrichment_status": enrichment_status,
            "enriched_at": datetime.now(UTC),
        }
