from collections import Counter
import re

from app.models.taste_profile import TasteProfile
from app.models.user import User
from app.repositories.taste_profile import TasteProfileRepository
from app.repositories.taste_seed import TasteSeedRepository


class TasteProfileService:
    def __init__(
        self,
        taste_seed_repository: TasteSeedRepository,
        taste_profile_repository: TasteProfileRepository,
    ) -> None:
        self.taste_seed_repository = taste_seed_repository
        self.taste_profile_repository = taste_profile_repository

    NORMALIZATION_RULES = {
        "not stuffy": {"avoid": ["stuffy", "overly formal"]},
        "feels real": {"vibe": ["grounded", "authentic", "unpretentious"]},
        "neighborhood feel": {"vibe": ["neighborhood", "local"]},
        "strong food": {"food_style": ["strong food identity"]},
        "creative": {"food_style": ["creative"]},
        "lively": {"vibe": ["lively"]},
        "stylish": {"vibe": ["stylish"]},
        "warm": {"vibe": ["warm"]},
    }

    EMPTY_STRUCTURED_ATTRIBUTES = {
        "vibe": [],
        "food_style": [],
        "service_style": [],
        "avoid": [],
        "tourist_tolerance": [],
        "novelty_preference": [],
    }

    @classmethod
    def _append_unique(cls, target: list[str], values: list[str]) -> None:
        for value in values:
            if value not in target:
                target.append(value)

    @classmethod
    def _parse_note_attributes(cls, notes: list[str]) -> dict[str, list[str]]:
        structured = {key: [] for key in cls.EMPTY_STRUCTURED_ATTRIBUTES}

        for raw_note in notes:
            note = raw_note.lower()

            phrase_matches: list[tuple[int, dict[str, list[str]]]] = []
            for phrase, mapping in cls.NORMALIZATION_RULES.items():
                index = note.find(phrase)
                if index >= 0:
                    phrase_matches.append((index, mapping))
            for _, mapping in sorted(phrase_matches, key=lambda item: item[0]):
                for field, values in mapping.items():
                    cls._append_unique(structured[field], values)

            if "friendly" in note or "welcoming" in note:
                cls._append_unique(structured["service_style"], ["friendly"])
            if "attentive" in note:
                cls._append_unique(structured["service_style"], ["attentive"])
            if "casual" in note:
                cls._append_unique(structured["service_style"], ["casual"])
            if "tasting menu" in note or "chef-driven" in note:
                cls._append_unique(structured["food_style"], ["chef-driven"])
            if "touristy" in note:
                cls._append_unique(structured["tourist_tolerance"], ["low tolerance for touristy spots"])
            if "hidden gem" in note or "off the beaten path" in note:
                cls._append_unique(structured["novelty_preference"], ["discovery-oriented"])
            if "classic" in note or "traditional" in note:
                cls._append_unique(structured["novelty_preference"], ["balanced between classic and new"])
            if "experimental" in note or "inventive" in note:
                cls._append_unique(structured["novelty_preference"], ["novelty-seeking"])

        return structured

    @classmethod
    def _merge_structured_attributes(cls, seeds) -> dict[str, list[str]]:
        merged = {key: [] for key in cls.EMPTY_STRUCTURED_ATTRIBUTES}
        for seed in seeds:
            parsed = cls._parse_note_attributes([seed.notes] if seed.notes else [])
            for field, values in parsed.items():
                cls._append_unique(merged[field], values)
        return merged

    @staticmethod
    def _summarize_profile(*, preferred_cities: list[str], structured: dict[str, list[str]], has_loves: bool) -> str:
        vibe = ", ".join(structured["vibe"][:3]) or "grounded"
        food_style = ", ".join(structured["food_style"][:2]) or "clear food identity"
        service_style = ", ".join(structured["service_style"][:2]) or "comfortable service"
        avoid = ", ".join(structured["avoid"][:2])
        city_phrase = f"in places like {', '.join(preferred_cities[:2])}" if preferred_cities else "when traveling"

        summary = (
            f"This diner responds best to {vibe} rooms {city_phrase}, with {food_style} and {service_style}."
        )
        if avoid:
            summary += f" They actively avoid {avoid} experiences."
        elif not has_loves:
            summary += " The profile is weighted more by stated dislikes than explicit favorites."
        return summary

    def generate_for_user(self, user: User) -> TasteProfile:
        seeds = self.taste_seed_repository.list_for_user(user.id)
        if not seeds:
            summary = "Open-minded diner profile inferred from no explicit seed restaurants yet."
            attributes_json = {
                "loved_restaurants": [],
                "disliked_restaurants": [],
                "preferred_cities": [user.home_city] if user.home_city else [],
                "preferred_keywords": ["local", "welcoming", "well-reviewed"],
                "avoided_keywords": [],
                "vibe": ["welcoming", "unfussy"],
                "food_style": ["clear food identity"],
                "service_style": ["comfortable"],
                "avoid": [],
                "tourist_tolerance": ["open but selective"],
                "novelty_preference": ["balanced"],
                "sentiment_breakdown": {"love": 0, "dislike": 0},
                "default_profile": True,
            }
            return self.taste_profile_repository.upsert(
                user_id=user.id,
                summary=summary,
                attributes_json=attributes_json,
            )

        loved = [seed for seed in seeds if seed.sentiment.value == "love"]
        disliked = [seed for seed in seeds if seed.sentiment.value == "dislike"]
        preferred_cities = [city for city, _ in Counter(seed.city for seed in loved or seeds).most_common(3)]
        structured_loves = self._merge_structured_attributes(loved)
        structured_dislikes = self._merge_structured_attributes(disliked)
        structured = {
            "vibe": list(structured_loves["vibe"]),
            "food_style": list(structured_loves["food_style"]),
            "service_style": list(structured_loves["service_style"]),
            "avoid": list(structured_loves["avoid"])
            + list(structured_dislikes["vibe"])
            + list(structured_dislikes["food_style"])
            + list(structured_dislikes["avoid"]),
            "tourist_tolerance": list(structured_loves["tourist_tolerance"] or structured_dislikes["tourist_tolerance"]),
            "novelty_preference": list(structured_loves["novelty_preference"] or structured_dislikes["novelty_preference"]),
        }
        if not structured["tourist_tolerance"]:
            structured["tourist_tolerance"] = ["prefers local-leaning places"]
        if not structured["novelty_preference"]:
            structured["novelty_preference"] = ["balanced"]

        preferred_keywords = structured["vibe"] + structured["food_style"] + structured["service_style"]
        avoided_keywords = structured["avoid"]
        summary = self._summarize_profile(
            preferred_cities=preferred_cities,
            structured=structured,
            has_loves=bool(loved),
        )

        attributes_json = {
            "loved_restaurants": [seed.name for seed in loved],
            "disliked_restaurants": [seed.name for seed in disliked],
            "preferred_cities": preferred_cities,
            "preferred_keywords": preferred_keywords,
            "avoided_keywords": avoided_keywords,
            "vibe": structured["vibe"],
            "food_style": structured["food_style"],
            "service_style": structured["service_style"],
            "avoid": structured["avoid"],
            "tourist_tolerance": structured["tourist_tolerance"],
            "novelty_preference": structured["novelty_preference"],
            "sentiment_breakdown": {"love": len(loved), "dislike": len(disliked)},
            "default_profile": False,
        }

        return self.taste_profile_repository.upsert(
            user_id=user.id,
            summary=summary,
            attributes_json=attributes_json,
        )
