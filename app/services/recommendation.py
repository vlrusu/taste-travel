from typing import Any

from app.models.enums import FeedbackType
from app.integrations.google_places import GooglePlacesClient
from app.integrations.mock_recommendations import build_mock_recommendation_candidates
from app.models.recommendation import Recommendation
from app.models.user import User
from app.repositories.recommendation import FeedbackRepository, RecommendationRepository
from app.repositories.taste_profile import TasteProfileRepository
from app.services.restaurant_identity import infer_restaurant_identity
from app.schemas.recommendation import RecommendationContextRequest, RecommendationLocationRequest


class RecommendationService:
    def __init__(
        self,
        recommendation_repository: RecommendationRepository,
        taste_profile_repository: TasteProfileRepository,
        feedback_repository: FeedbackRepository | None = None,
        google_places_client: GooglePlacesClient | None = None,
    ) -> None:
        self.recommendation_repository = recommendation_repository
        self.taste_profile_repository = taste_profile_repository
        self.feedback_repository = feedback_repository
        self.google_places_client = google_places_client or GooglePlacesClient()

    @staticmethod
    def _price_to_int(price_level: str | None) -> int:
        return len(price_level or "")

    @classmethod
    def _restaurant_key(cls, restaurant: dict[str, Any]) -> str:
        place_id = restaurant.get("google_place_id") or restaurant.get("source_place_id")
        if isinstance(place_id, str) and place_id:
            return f"place:{place_id}"
        name = str(restaurant.get("name") or "").strip().lower()
        city = str(restaurant.get("city") or "").strip().lower()
        return f"name_city:{name}|{city}"

    @classmethod
    def _build_feedback_signals(cls, recent_feedback: list[tuple[Any, Recommendation]]) -> dict[str, Any]:
        signals = {
            "preferred_vibes": set(),
            "preferred_cuisines": set(),
            "avoid_vibes": set(),
            "avoid_cuisines": set(),
            "avoid_formal": 0,
            "avoid_touristy": 0,
            "avoid_expensive": 0,
            "prefer_local": 0,
            "blocked_restaurant_keys": set(),
        }
        for feedback, recommendation in recent_feedback:
            restaurant = recommendation.restaurant_json
            vibe_tags = set(restaurant.get("vibe_tags", []))
            cuisine_tags = set(restaurant.get("cuisine_tags", []))
            feedback_type = feedback.feedback_type

            if feedback_type in {FeedbackType.PERFECT, FeedbackType.SAVED}:
                signals["preferred_vibes"].update(vibe_tags)
                signals["preferred_cuisines"].update(cuisine_tags)
                if restaurant.get("tourist_profile") == "local-leaning":
                    signals["prefer_local"] += 1
                continue

            if feedback_type in {FeedbackType.NOT_MY_VIBE, FeedbackType.DISMISSED}:
                signals["avoid_vibes"].update(vibe_tags)
                signals["avoid_cuisines"].update(cuisine_tags)
                signals["blocked_restaurant_keys"].add(cls._restaurant_key(restaurant))
            if feedback_type == FeedbackType.TOO_FORMAL:
                signals["avoid_formal"] += 1
                signals["avoid_vibes"].update(tag for tag in vibe_tags if tag in {"refined", "stylish", "chef-driven"})
                signals["avoid_cuisines"].update(tag for tag in cuisine_tags if tag in {"tasting-menu"})
                signals["blocked_restaurant_keys"].add(cls._restaurant_key(restaurant))
            if feedback_type == FeedbackType.TOO_TOURISTY:
                signals["avoid_touristy"] += 1
                signals["blocked_restaurant_keys"].add(cls._restaurant_key(restaurant))
            if feedback_type == FeedbackType.TOO_EXPENSIVE:
                signals["avoid_expensive"] += 1
                signals["blocked_restaurant_keys"].add(cls._restaurant_key(restaurant))

        return signals

    @classmethod
    def _score_candidate(
        cls,
        *,
        restaurant: dict[str, Any],
        profile: dict[str, Any],
        feedback_signals: dict[str, Any],
        budget: str | None,
        special_request: str | None,
    ) -> tuple[dict[str, float], list[str], list[str]]:
        vibe_tags = restaurant["vibe_tags"]
        cuisine_tags = restaurant["cuisine_tags"]
        avoid = set(profile.get("avoid", []))
        profile_vibe = set(profile.get("vibe", []))
        profile_food_style = set(profile.get("food_style", []))
        tourist_pref = set(profile.get("tourist_tolerance", []))
        positive_profile_traits = {str(value).replace("_", " ") for value in profile.get("positive_traits", [])}
        negative_profile_traits = {str(value).replace("_", " ") for value in profile.get("negative_traits", [])}
        liked_archetypes = {str(value).replace(" ", "_") for value in profile.get("liked_archetypes", [])}
        special_request_lower = (special_request or "").lower()
        verified_seed_count = len(profile.get("verified_place_restaurants", []))
        derived_signal_strength = 1.25 if verified_seed_count else 1.0
        restaurant_vibes = set(vibe_tags)
        restaurant_cuisines = set(cuisine_tags)
        identity = infer_restaurant_identity(
            name=restaurant["name"],
            raw_types=restaurant.get("raw_types"),
            cuisine_tags=cuisine_tags,
            vibe_tags=vibe_tags,
            food_style_tags=[tag.replace(" ", "_").replace("-", "_") for tag in cuisine_tags],
            price_level=restaurant.get("price_level"),
            formality_score=restaurant["formality_score"],
            tourist_profile=restaurant["tourist_profile"],
            rating=restaurant.get("rating"),
            user_ratings_total=restaurant.get("user_ratings_total"),
            text_blobs=[restaurant.get("address"), " ".join(cuisine_tags), " ".join(vibe_tags)],
        )
        candidate_positive_traits = {value.replace("_", " ") for value in identity["positive_traits"]}
        candidate_negative_traits = {value.replace("_", " ") for value in identity["negative_traits"]}
        primary_archetype = identity["primary_archetype"]
        secondary_archetypes = set(identity["secondary_archetypes"])

        positive_terms = {"local-favorite", "neighborhood", "shared-plates", "market-driven", "casual", "grounded", "authentic", "warm"}
        vibe_match_score = sum((0.12 * derived_signal_strength) for tag in vibe_tags if tag in profile_vibe or tag in positive_terms)
        food_style_match_score = sum((0.14 * derived_signal_strength) for tag in cuisine_tags if tag in profile_food_style or tag in {"market-driven", "strong food identity", "creative", "small plates", "seafood", "regional"})
        archetype_match_score = 0.0
        if primary_archetype in liked_archetypes:
            archetype_match_score += 0.32
        elif secondary_archetypes & liked_archetypes:
            archetype_match_score += 0.18
        elif primary_archetype in {"corporate_seafood_steak", "business_district_dining", "hotel_adjacent_upscale"} and liked_archetypes & {
            "corporate_seafood_steak",
            "business_district_dining",
            "hotel_adjacent_upscale",
            "tourist_favorite",
        }:
            archetype_match_score += 0.46

        food_identity_score = 0.24 * float(identity["food_identity_score"])
        character_score = 0.22 * float(identity["character_score"])
        localness_score = 0.22 * float(identity["localness_score"])

        formality_penalty = 0.0
        if restaurant["formality_score"] >= 0.7 and ("overly formal" in avoid or "stuffy" in avoid):
            formality_penalty += 0.45
        if {"refined", "tasting-menu"} & set(vibe_tags + cuisine_tags) and not ({"refined", "formal"} & profile_vibe):
            formality_penalty += 0.22
        if "not too formal" in special_request_lower and restaurant["formality_score"] >= 0.6:
            formality_penalty += 0.5

        avoid_penalty = 0.0
        if "stuffy" in avoid and "refined" in vibe_tags:
            avoid_penalty += 0.2
        if "overly formal" in avoid and restaurant["formality_score"] >= 0.6:
            avoid_penalty += 0.2
        if {"corporate", "generic upscale", "safe luxury", "business district", "tourist heavy"} & negative_profile_traits:
            if "generic upscale" in candidate_negative_traits:
                avoid_penalty += 0.18
            if "tourist heavy" in candidate_negative_traits:
                avoid_penalty += 0.16

        budget_match_score = 0.0
        requested_budget = cls._price_to_int(budget)
        restaurant_budget = cls._price_to_int(restaurant["price_level"])
        if requested_budget:
            if restaurant_budget == requested_budget:
                budget_match_score += 0.24
            elif restaurant_budget == requested_budget + 1:
                budget_match_score -= 0.18
            elif restaurant_budget > requested_budget + 1:
                budget_match_score -= 0.32
            elif restaurant_budget == requested_budget - 1:
                budget_match_score += 0.08

        tourist_fit_score = 0.0
        if "prefers local-leaning places" in tourist_pref:
            if restaurant["tourist_profile"] == "local-leaning":
                tourist_fit_score += 0.18
            elif restaurant["tourist_profile"] == "mixed":
                tourist_fit_score += 0.05
            else:
                tourist_fit_score -= 0.12

        special_request_score = 0.0
        if "shared" in special_request_lower and "shared-plates" in vibe_tags:
            special_request_score += 0.16
        if "local" in special_request_lower and restaurant["tourist_profile"] == "local-leaning":
            special_request_score += 0.16
        if "casual" in special_request_lower and "casual" in vibe_tags:
            special_request_score += 0.12
        if "memorable" in special_request_lower:
            if "strong food identity" in cuisine_tags:
                special_request_score += 0.14
            if "stylish" in vibe_tags or restaurant["tourist_profile"] == "local-leaning":
                special_request_score += 0.1
        if verified_seed_count and ("warm" in vibe_tags or "grounded" in vibe_tags or "local-favorite" in vibe_tags):
            special_request_score += 0.05

        positive_trait_match_score = 0.0
        if positive_profile_traits:
            positive_trait_match_score += min(0.25, 0.06 * len(positive_profile_traits & candidate_positive_traits))
        profile_prefers_upscale = bool({"polished luxury", "safe luxury", "business district", "luxury consistency"} & positive_profile_traits)
        upscale_affinity_score = 0.0
        if profile_prefers_upscale:
            upscale_affinity_score += min(
                0.36,
                0.1 * len(
                    {
                        "polished luxury",
                        "safe luxury",
                        "business district",
                        "luxury consistency",
                    }
                    & candidate_positive_traits
                ),
            )
        upscale_mismatch_penalty = 0.0
        if profile_prefers_upscale and not (
            {"polished luxury", "safe luxury", "business district", "luxury consistency"} & candidate_positive_traits
            or primary_archetype in {"corporate_seafood_steak", "business_district_dining", "hotel_adjacent_upscale", "tourist_favorite"}
        ):
            upscale_mismatch_penalty += 0.72

        corporate_penalty = 0.0
        dislikes_corporate = bool({"corporate", "business district", "chain feeling", "convention dining"} & negative_profile_traits)
        dislikes_touristy = bool({"tourist heavy", "business district"} & negative_profile_traits)
        dislikes_generic_upscale = bool({"generic upscale", "safe luxury", "hotel restaurant feel", "overly formal"} & negative_profile_traits)

        if dislikes_corporate and "corporate" in candidate_negative_traits:
            corporate_penalty += 0.28
        if dislikes_corporate and ("business district" in candidate_negative_traits or "hotel restaurant feel" in candidate_negative_traits):
            corporate_penalty += 0.16

        tourist_penalty = 0.0
        if dislikes_touristy and ("tourist heavy" in candidate_negative_traits or restaurant["tourist_profile"] == "destination"):
            tourist_penalty += 0.22

        generic_upscale_penalty = 0.0
        if dislikes_generic_upscale and {"generic upscale", "safe luxury", "convention dining"} & candidate_negative_traits:
            generic_upscale_penalty += 0.24
        if dislikes_generic_upscale and "overly formal" in candidate_negative_traits:
            generic_upscale_penalty += 0.12

        feedback_adjustment_score = 0.0
        preferred_vibes = feedback_signals.get("preferred_vibes", set())
        preferred_cuisines = feedback_signals.get("preferred_cuisines", set())
        avoid_vibes = feedback_signals.get("avoid_vibes", set())
        avoid_cuisines = feedback_signals.get("avoid_cuisines", set())

        if preferred_vibes:
            feedback_adjustment_score += min(0.18, 0.05 * len(restaurant_vibes & preferred_vibes))
        if preferred_cuisines:
            feedback_adjustment_score += min(0.18, 0.06 * len(restaurant_cuisines & preferred_cuisines))
        if avoid_vibes & restaurant_vibes:
            feedback_adjustment_score -= min(0.2, 0.07 * len(avoid_vibes & restaurant_vibes))
        if avoid_cuisines & restaurant_cuisines:
            feedback_adjustment_score -= min(0.2, 0.08 * len(avoid_cuisines & restaurant_cuisines))
        if feedback_signals.get("avoid_formal", 0) and restaurant["formality_score"] >= 0.6:
            feedback_adjustment_score -= 0.24
        if feedback_signals.get("avoid_touristy", 0):
            if restaurant["tourist_profile"] == "destination":
                feedback_adjustment_score -= 0.2
            elif restaurant["tourist_profile"] == "mixed":
                feedback_adjustment_score -= 0.08
        if feedback_signals.get("avoid_expensive", 0) and cls._price_to_int(restaurant["price_level"]) >= 3:
            feedback_adjustment_score -= 0.22
        if feedback_signals.get("prefer_local", 0) and restaurant["tourist_profile"] == "local-leaning":
            feedback_adjustment_score += 0.08

        components = {
            "vibe_match_score": round(vibe_match_score, 3),
            "food_style_match_score": round(food_style_match_score, 3),
            "archetype_match_score": round(archetype_match_score, 3),
            "positive_trait_match_score": round(positive_trait_match_score, 3),
            "upscale_affinity_score": round(upscale_affinity_score, 3),
            "upscale_mismatch_penalty": round(upscale_mismatch_penalty, 3),
            "character_score": round(character_score, 3),
            "localness_score": round(localness_score, 3),
            "food_identity_score": round(food_identity_score, 3),
            "avoid_penalty": round(avoid_penalty, 3),
            "budget_match_score": round(budget_match_score, 3),
            "formality_penalty": round(formality_penalty, 3),
            "tourist_fit_score": round(tourist_fit_score, 3),
            "special_request_score": round(special_request_score, 3),
            "feedback_adjustment_score": round(feedback_adjustment_score, 3),
            "corporate_penalty": round(corporate_penalty, 3),
            "tourist_penalty": round(tourist_penalty, 3),
            "generic_upscale_penalty": round(generic_upscale_penalty, 3),
        }

        matched_traits: list[str] = []
        if primary_archetype in liked_archetypes:
            matched_traits.append(f"closer to your {primary_archetype.replace('_', ' ')} taste")
        if "local-favorite" in vibe_tags or "neighborhood" in vibe_tags:
            matched_traits.append("local feel")
        if "strong food identity" in cuisine_tags:
            matched_traits.append("strong food identity")
        if "shared-plates" in vibe_tags:
            matched_traits.append("lively shared-plates energy")
        if {"warm", "neighborhood"} & set(vibe_tags):
            matched_traits.append("warm neighborhood vibe")
        if "stylish" in vibe_tags and restaurant["formality_score"] < 0.6:
            matched_traits.append("stylish without feeling formal")
        if {"characterful", "food forward", "independent"} & candidate_positive_traits:
            matched_traits.append("characterful food-first identity")
        if feedback_adjustment_score > 0.12:
            matched_traits.append("similar to places you marked as a good fit")

        caution_traits: list[str] = []
        if corporate_penalty > 0:
            caution_traits.append("it reads as more corporate than your seeds usually suggest")
        if generic_upscale_penalty > 0:
            caution_traits.append("it likely feels too generic-upscale for your profile")
        if tourist_penalty > 0:
            caution_traits.append("it looks more tourist-heavy than your usual picks")
        if upscale_mismatch_penalty > 0:
            caution_traits.append("it reads more casual-local than your polished destination picks")
        if formality_penalty >= 0.22:
            caution_traits.append("it may feel more refined than you usually prefer")
        if budget_match_score < 0:
            caution_traits.append("it stretches the requested budget")
        if restaurant["tourist_profile"] == "destination" and "prefers local-leaning places" in tourist_pref:
            caution_traits.append("it reads more destination-driven than local")
        if feedback_signals.get("avoid_formal", 0) and restaurant["formality_score"] >= 0.6:
            caution_traits.append("you recently pushed down places that felt too formal")
        if feedback_signals.get("avoid_touristy", 0) and restaurant["tourist_profile"] == "destination":
            caution_traits.append("you recently pushed down places that felt too touristy")
        if feedback_signals.get("avoid_expensive", 0) and cls._price_to_int(restaurant["price_level"]) >= 3:
            caution_traits.append("you recently pushed down places that felt too expensive")

        return components, matched_traits, caution_traits

    @staticmethod
    def _build_explanation(name: str, matched_traits: list[str], caution_traits: list[str], seed_restaurants: list[str]) -> str:
        parts: list[str] = []
        if matched_traits:
            if seed_restaurants:
                parts.append(f"{name} feels closer to the {seed_restaurants[0]} side of your taste: {', '.join(matched_traits[:2])}.")
            else:
                parts.append(f"{name} stands out for its {', '.join(matched_traits[:2])}.")
        if len(matched_traits) > 2:
            parts.append(f"It also brings {matched_traits[2]}")
        if caution_traits:
            parts.append(f"Ranked lower if needed because {caution_traits[0]}.")
        return " ".join(parts) or f"{name} is a balanced fit for this trip."

    def generate_for_user(
        self,
        *,
        user: User,
        location: RecommendationLocationRequest,
        context: RecommendationContextRequest,
    ) -> list[Recommendation]:
        profile = self.taste_profile_repository.get_for_user(user.id)
        attributes = profile.attributes_json if profile else {}
        recent_feedback = self.feedback_repository.list_recent_for_user(user_id=user.id) if self.feedback_repository else []
        feedback_signals = self._build_feedback_signals(recent_feedback)
        resolved_location = self._resolve_location(location)
        blocked_restaurant_keys = feedback_signals.get("blocked_restaurant_keys", set())
        candidates = self._load_candidates(
            location=resolved_location,
            context=context,
            blocked_restaurant_keys=blocked_restaurant_keys,
        )
        candidates = [
            candidate
            for candidate in candidates
            if self._restaurant_key(candidate["restaurant_json"]) not in blocked_restaurant_keys
        ]
        ranked_payloads: list[dict[str, Any]] = []
        for candidate in candidates:
            restaurant = candidate["restaurant_json"]
            components, matched_traits, caution_traits = self._score_candidate(
                restaurant=restaurant,
                profile=attributes,
                feedback_signals=feedback_signals,
                budget=context.budget,
                special_request=context.special_request,
            )
            score = round(
                (
                    0.5
                    + components["vibe_match_score"]
                    + components["food_style_match_score"]
                    + components["archetype_match_score"]
                    + components["positive_trait_match_score"]
                    + components["upscale_affinity_score"]
                    + components["character_score"]
                    + components["localness_score"]
                    + components["food_identity_score"]
                    + components["budget_match_score"]
                    + components["tourist_fit_score"]
                    + components["special_request_score"]
                    + components["feedback_adjustment_score"]
                    - components["avoid_penalty"]
                    - components["formality_penalty"]
                    - components["corporate_penalty"]
                    - components["tourist_penalty"]
                    - components["generic_upscale_penalty"]
                    - components["upscale_mismatch_penalty"]
                ),
                3,
            )
            ranked_payloads.append(
                {
                    "request_context_json": {
                        "location": {
                            "city": resolved_location.city,
                            "lat": resolved_location.lat,
                            "lon": resolved_location.lon,
                        },
                        "context": {
                            "budget": context.budget,
                            "max_distance_meters": context.max_distance_meters,
                            "special_request": context.special_request,
                        },
                    },
                    "restaurant_json": restaurant,
                    "score": score,
                    "why": self._build_explanation(
                        restaurant["name"],
                        matched_traits,
                        caution_traits,
                        attributes.get("loved_restaurants", [])[:3],
                    ),
                    "anchors_json": {
                        "seed_restaurants": attributes.get("loved_restaurants", [])[:3],
                        "matched_traits": matched_traits,
                        "caution_traits": caution_traits,
                        "score_breakdown": components,
                    },
                }
            )

        ranked_payloads.sort(key=lambda item: item["score"], reverse=True)
        recommendations: list[Recommendation] = []
        for payload in ranked_payloads[:5]:
            recommendations.append(
                self.recommendation_repository.create(
                    user_id=user.id,
                    request_context_json=payload["request_context_json"],
                    restaurant_json=payload["restaurant_json"],
                    score=payload["score"],
                    why=payload["why"],
                    anchors_json=payload["anchors_json"],
                )
            )
        return recommendations

    def _resolve_location(self, location: RecommendationLocationRequest) -> RecommendationLocationRequest:
        if location.lat is not None and location.lon is not None:
            return location

        try:
            resolved = self.google_places_client.geocode_city(city=location.city, country="")
        except Exception:
            return location

        if resolved is None:
            return location

        lat, lon = resolved
        return RecommendationLocationRequest(city=location.city, lat=lat, lon=lon)

    def _load_candidates(
        self,
        *,
        location: RecommendationLocationRequest,
        context: RecommendationContextRequest,
        blocked_restaurant_keys: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        fake_candidates = build_mock_recommendation_candidates(
            destination_city=location.city,
            destination_country="",
        )
        blocked_restaurant_keys = blocked_restaurant_keys or set()
        base_radius = context.max_distance_meters or 2000
        if blocked_restaurant_keys:
            search_radii = [base_radius, max(base_radius * 2, 4000), max(base_radius * 3, 7000)]
        else:
            search_radii = [base_radius]

        google_candidates: list[dict[str, Any]] = []
        seen_google_keys: set[str] = set()
        try:
            for radius in search_radii:
                batch = self.google_places_client.search_restaurants(
                    city=location.city,
                    country="",
                    lat=location.lat,
                    lon=location.lon,
                    radius_meters=radius,
                    meal_type="dinner",
                )
                for candidate in batch:
                    key = self._restaurant_key(candidate["restaurant_json"])
                    if key in seen_google_keys:
                        continue
                    seen_google_keys.add(key)
                    google_candidates.append(candidate)

                remaining_google = [
                    candidate
                    for candidate in google_candidates
                    if self._restaurant_key(candidate["restaurant_json"]) not in blocked_restaurant_keys
                ]
                if len(remaining_google) >= 5:
                    return google_candidates
        except Exception:
            return fake_candidates

        if not google_candidates:
            return fake_candidates
        return google_candidates
