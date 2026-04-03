from collections import Counter

from app.models.taste_profile import TasteProfile
from app.models.user import User
from app.repositories.taste_profile import TasteProfileRepository
from app.repositories.taste_seed import TasteSeedRepository


class TasteProfileService:
    LOCAL_ARCHETYPES = {
        "neighborhood_wine_bar",
        "chef_driven_small_plates",
        "polished_local_bistro",
        "design_forward_casual",
        "everyday_neighborhood_spot",
        "local_institution",
    }

    UPSCALE_ARCHETYPES = {
        "corporate_seafood_steak",
        "hotel_adjacent_upscale",
        "business_district_dining",
        "tourist_favorite",
        "destination_tasting_room",
    }

    LOCAL_POSITIVE_TRAITS = {
        "neighborhood_favorite",
        "local_leaning",
        "chef_driven",
        "independent",
        "characterful",
        "food_forward",
        "culturally_specific",
        "warm",
        "grounded",
        "unpretentious",
        "strong_food_identity",
    }

    UPSCALE_POSITIVE_TRAITS = {
        "polished_luxury",
        "safe_luxury",
        "business_district",
        "luxury_consistency",
    }

    INFERRED_LOCAL_ANTI_SIGNALS = [
        "corporate",
        "generic_upscale",
        "tourist_heavy",
        "business_district",
        "chain_feeling",
        "safe_luxury",
        "convention_dining",
    ]

    DERIVED_TRAIT_TO_PROFILE = {
        "vibe": {
            "buzzy": "buzzy",
            "calm": "calm",
            "energetic": "energetic",
            "grounded": "grounded",
            "local": "local",
            "lively": "lively",
            "neighborhood": "neighborhood",
            "romantic": "romantic",
            "stylish": "stylish",
            "warm": "warm",
            "unpretentious": "unpretentious",
        },
        "food_style": {
            "chef_driven": "chef-driven",
            "classic": "classic",
            "comfort_food": "comfort food",
            "creative": "creative",
            "experimental": "experimental",
            "strong_food_identity": "strong food identity",
            "traditional": "traditional",
        },
        "formality": {
            "casual": "casual",
            "casual_polished": "casual polished",
            "polished": "polished",
            "formal": "formal",
        },
        "social_feel": {
            "neighborhood_favorite": "neighborhood favorite",
            "destination": "destination",
            "tourist_heavy": "touristy",
            "local_leaning": "prefers local-leaning places",
        },
        "use_case": {
            "date_night": "date night",
            "groups": "groups",
            "everyday": "everyday",
            "special_occasion": "special occasion",
            "late_night": "late night",
        },
        "cuisine_style": {
            "small_plates": "small plates",
            "seafood": "seafood",
            "tapas": "tapas",
            "bistro": "bistro",
            "tasting_menu": "tasting-menu",
            "regional": "regional",
            "wine_bar": "wine bar",
            "cafe": "cafe",
            "bakery": "bakery",
        },
    }

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
        "positive_traits": [],
        "negative_traits": [],
        "liked_archetypes": [],
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

    @classmethod
    def _merge_place_attributes(cls, seeds) -> dict[str, list[str]]:
        merged = {key: [] for key in cls.EMPTY_STRUCTURED_ATTRIBUTES}
        for seed in seeds:
            traits = seed.place_traits_json or {}
            for field in cls.EMPTY_STRUCTURED_ATTRIBUTES:
                values = traits.get(field, [])
                if isinstance(values, list):
                    cls._append_unique(merged[field], [str(value) for value in values])
            likely_formality = traits.get("likely_formality")
            if likely_formality == "formal":
                cls._append_unique(merged["avoid"], ["overly formal"])
            if likely_formality == "casual":
                cls._append_unique(merged["service_style"], ["casual"])
            tourist_profile = traits.get("tourist_profile")
            if tourist_profile == "local-leaning":
                cls._append_unique(merged["tourist_tolerance"], ["prefers local-leaning places"])
            elif tourist_profile == "destination":
                cls._append_unique(merged["avoid"], ["touristy"])
            if traits.get("price_band") in {"$", "$$"}:
                cls._append_unique(merged["service_style"], ["approachable"])
            if isinstance(traits.get("positive_traits"), list):
                cls._append_unique(merged["positive_traits"], [str(value).replace("_", " ") for value in traits["positive_traits"]])
            if isinstance(traits.get("negative_traits"), list):
                cls._append_unique(merged["negative_traits"], [str(value).replace("_", " ") for value in traits["negative_traits"]])
            if traits.get("primary_archetype"):
                cls._append_unique(merged["liked_archetypes"], [str(traits["primary_archetype"]).replace("_", " ")])
        return merged

    @classmethod
    def _merge_derived_seed_attributes(cls, seeds) -> dict[str, list[str]]:
        merged = {key: [] for key in cls.EMPTY_STRUCTURED_ATTRIBUTES}
        for seed in seeds:
            traits = seed.derived_traits_json or {}
            vibe_values = [cls.DERIVED_TRAIT_TO_PROFILE["vibe"][value] for value in traits.get("vibe", []) if value in cls.DERIVED_TRAIT_TO_PROFILE["vibe"]]
            food_style_values = [cls.DERIVED_TRAIT_TO_PROFILE["food_style"][value] for value in traits.get("food_style", []) if value in cls.DERIVED_TRAIT_TO_PROFILE["food_style"]]
            formality_values = [cls.DERIVED_TRAIT_TO_PROFILE["formality"][value] for value in traits.get("formality", []) if value in cls.DERIVED_TRAIT_TO_PROFILE["formality"]]
            social_feel_values = [cls.DERIVED_TRAIT_TO_PROFILE["social_feel"][value] for value in traits.get("social_feel", []) if value in cls.DERIVED_TRAIT_TO_PROFILE["social_feel"]]
            use_case_values = [cls.DERIVED_TRAIT_TO_PROFILE["use_case"][value] for value in traits.get("use_case", []) if value in cls.DERIVED_TRAIT_TO_PROFILE["use_case"]]
            cuisine_style_values = [cls.DERIVED_TRAIT_TO_PROFILE["cuisine_style"][value] for value in traits.get("cuisine_style", []) if value in cls.DERIVED_TRAIT_TO_PROFILE["cuisine_style"]]

            cls._append_unique(merged["vibe"], vibe_values)
            cls._append_unique(merged["food_style"], food_style_values + cuisine_style_values)
            cls._append_unique(merged["service_style"], formality_values)
            cls._append_unique(merged["tourist_tolerance"], [value for value in social_feel_values if "local-leaning" in value])
            if "touristy" in social_feel_values:
                cls._append_unique(merged["avoid"], ["touristy"])
            if "formal" in formality_values:
                cls._append_unique(merged["avoid"], ["overly formal"])
            if "special occasion" in use_case_values:
                cls._append_unique(merged["novelty_preference"], ["balanced"])
            elif use_case_values:
                cls._append_unique(merged["novelty_preference"], ["discovery-oriented"])
            cls._append_unique(
                merged["positive_traits"],
                [str(value).replace("_", " ") for value in traits.get("positive_traits", []) if isinstance(value, str)],
            )
            cls._append_unique(
                merged["negative_traits"],
                [str(value).replace("_", " ") for value in traits.get("negative_traits", []) if isinstance(value, str)],
            )
            archetype = traits.get("primary_archetype")
            if isinstance(archetype, str):
                cls._append_unique(merged["liked_archetypes"], [archetype.replace("_", " ")])
        return merged

    @classmethod
    def _infer_seed_set_anti_signals(cls, loved_seeds) -> list[str]:
        archetypes = [
            str((seed.derived_traits_json or {}).get("primary_archetype") or "")
            for seed in loved_seeds
            if seed.derived_traits_json
        ]
        local_archetype_count = sum(1 for value in archetypes if value in cls.LOCAL_ARCHETYPES)
        upscale_archetype_count = sum(1 for value in archetypes if value in cls.UPSCALE_ARCHETYPES)
        positive_traits = {
            str(value)
            for seed in loved_seeds
            for value in (seed.derived_traits_json or {}).get("positive_traits", [])
            if isinstance(value, str)
        }
        if upscale_archetype_count >= 1 or positive_traits & cls.UPSCALE_POSITIVE_TRAITS:
            return []
        if local_archetype_count >= 2 or len(positive_traits & cls.LOCAL_POSITIVE_TRAITS) >= 3:
            return list(cls.INFERRED_LOCAL_ANTI_SIGNALS)
        return []

    @classmethod
    def _combine_attributes(cls, note_attrs: dict[str, list[str]], place_attrs: dict[str, list[str]]) -> dict[str, list[str]]:
        combined = {key: [] for key in cls.EMPTY_STRUCTURED_ATTRIBUTES}
        for field in cls.EMPTY_STRUCTURED_ATTRIBUTES:
            cls._append_unique(combined[field], place_attrs[field])
            cls._append_unique(combined[field], note_attrs[field])
        return combined

    @staticmethod
    def _summarize_profile(*, preferred_cities: list[str], structured: dict[str, list[str]], has_loves: bool) -> str:
        vibe = ", ".join(structured["vibe"][:3]) or "grounded"
        food_style = ", ".join(structured["food_style"][:2]) or "clear food identity"
        service_style = ", ".join(structured["service_style"][:2]) or "comfortable service"
        avoid = ", ".join(structured["avoid"][:2])
        archetypes = ", ".join(structured["liked_archetypes"][:2]).replace("_", " ")
        city_phrase = f"in places like {', '.join(preferred_cities[:2])}" if preferred_cities else "when traveling"

        summary = f"This diner responds best to {vibe} rooms {city_phrase}, with {food_style} and {service_style}."
        if archetypes:
            summary += f" Their taste leans toward {archetypes} identities."
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
        structured_love_notes = self._merge_structured_attributes(loved)
        structured_dislike_notes = self._merge_structured_attributes(disliked)
        structured_love_places = self._merge_place_attributes(loved)
        structured_dislike_places = self._merge_place_attributes(disliked)
        structured_love_derived = self._merge_derived_seed_attributes(loved)
        structured_dislike_derived = self._merge_derived_seed_attributes(disliked)
        structured_love_places = self._combine_attributes(structured_love_places, structured_love_derived)
        structured_dislike_places = self._combine_attributes(structured_dislike_places, structured_dislike_derived)
        structured_loves = self._combine_attributes(structured_love_notes, structured_love_places)
        structured_dislikes = self._combine_attributes(structured_dislike_notes, structured_dislike_places)
        inferred_anti_signals = self._infer_seed_set_anti_signals(loved)
        structured = {
            "vibe": list(structured_loves["vibe"]),
            "food_style": list(structured_loves["food_style"]),
            "service_style": list(structured_loves["service_style"]),
            "avoid": list(structured_loves["avoid"])
            + list(structured_dislikes["vibe"])
            + list(structured_dislikes["food_style"])
            + list(structured_dislikes["avoid"])
            + [value.replace("_", " ") for value in inferred_anti_signals],
            "tourist_tolerance": list(structured_loves["tourist_tolerance"] or structured_dislikes["tourist_tolerance"]),
            "novelty_preference": list(structured_loves["novelty_preference"] or structured_dislikes["novelty_preference"]),
            "positive_traits": list(structured_loves["positive_traits"]),
            "negative_traits": list(structured_dislikes["negative_traits"]) + [value.replace("_", " ") for value in inferred_anti_signals],
            "liked_archetypes": list(structured_loves["liked_archetypes"]),
        }
        if not structured["tourist_tolerance"]:
            structured["tourist_tolerance"] = ["prefers local-leaning places"]
        if not structured["novelty_preference"]:
            structured["novelty_preference"] = ["balanced"]

        preferred_keywords = structured["vibe"] + structured["food_style"] + structured["service_style"]
        avoided_keywords = structured["avoid"] + structured["negative_traits"]
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
            "verified_place_restaurants": [seed.name for seed in seeds if seed.is_verified_place],
            "place_derived_traits": {
                "love": structured_love_places,
                "dislike": structured_dislike_places,
            },
            "seed_derived_traits": {
                "love": structured_love_derived,
                "dislike": structured_dislike_derived,
            },
            "vibe": structured["vibe"],
            "food_style": structured["food_style"],
            "service_style": structured["service_style"],
            "avoid": structured["avoid"],
            "positive_traits": structured["positive_traits"],
            "negative_traits": structured["negative_traits"],
            "liked_archetypes": structured["liked_archetypes"],
            "inferred_anti_signals": [value.replace("_", " ") for value in inferred_anti_signals],
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
