from typing import Any

from app.integrations.google_places import GooglePlacesClient
from app.integrations.mock_recommendations import build_mock_recommendation_candidates
from app.models.recommendation import Recommendation
from app.models.user import User
from app.repositories.recommendation import RecommendationRepository
from app.repositories.taste_profile import TasteProfileRepository
from app.schemas.recommendation import RecommendationContextRequest, RecommendationLocationRequest


class RecommendationService:
    def __init__(
        self,
        recommendation_repository: RecommendationRepository,
        taste_profile_repository: TasteProfileRepository,
        google_places_client: GooglePlacesClient | None = None,
    ) -> None:
        self.recommendation_repository = recommendation_repository
        self.taste_profile_repository = taste_profile_repository
        self.google_places_client = google_places_client or GooglePlacesClient()

    @staticmethod
    def _price_to_int(price_level: str | None) -> int:
        return len(price_level or "")

    @classmethod
    def _score_candidate(
        cls,
        *,
        restaurant: dict[str, Any],
        profile: dict[str, Any],
        budget: str | None,
        special_request: str | None,
    ) -> tuple[dict[str, float], list[str], list[str]]:
        vibe_tags = restaurant["vibe_tags"]
        cuisine_tags = restaurant["cuisine_tags"]
        avoid = set(profile.get("avoid", []))
        profile_vibe = set(profile.get("vibe", []))
        profile_food_style = set(profile.get("food_style", []))
        tourist_pref = set(profile.get("tourist_tolerance", []))
        special_request_lower = (special_request or "").lower()

        positive_terms = {"local-favorite", "neighborhood", "shared-plates", "market-driven", "casual", "grounded", "authentic", "warm"}
        vibe_match_score = sum(0.12 for tag in vibe_tags if tag in profile_vibe or tag in positive_terms)
        food_style_match_score = sum(0.14 for tag in cuisine_tags if tag in profile_food_style or tag in {"market-driven", "strong food identity", "creative"})

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

        components = {
            "vibe_match_score": round(vibe_match_score, 3),
            "food_style_match_score": round(food_style_match_score, 3),
            "avoid_penalty": round(avoid_penalty, 3),
            "budget_match_score": round(budget_match_score, 3),
            "formality_penalty": round(formality_penalty, 3),
            "tourist_fit_score": round(tourist_fit_score, 3),
            "special_request_score": round(special_request_score, 3),
        }

        matched_traits: list[str] = []
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

        caution_traits: list[str] = []
        if formality_penalty >= 0.22:
            caution_traits.append("it may feel more refined than you usually prefer")
        if budget_match_score < 0:
            caution_traits.append("it stretches the requested budget")
        if restaurant["tourist_profile"] == "destination" and "prefers local-leaning places" in tourist_pref:
            caution_traits.append("it reads more destination-driven than local")

        return components, matched_traits, caution_traits

    @staticmethod
    def _build_explanation(name: str, matched_traits: list[str], caution_traits: list[str]) -> str:
        parts: list[str] = []
        if matched_traits:
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
        resolved_location = self._resolve_location(location)
        candidates = self._load_candidates(location=resolved_location, context=context)
        ranked_payloads: list[dict[str, Any]] = []
        for candidate in candidates:
            restaurant = candidate["restaurant_json"]
            components, matched_traits, caution_traits = self._score_candidate(
                restaurant=restaurant,
                profile=attributes,
                budget=context.budget,
                special_request=context.special_request,
            )
            score = round(
                0.5
                + components["vibe_match_score"]
                + components["food_style_match_score"]
                + components["budget_match_score"]
                + components["tourist_fit_score"]
                + components["special_request_score"]
                - components["avoid_penalty"]
                - components["formality_penalty"],
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
                            "meal_type": context.meal_type,
                            "party_size": context.party_size,
                            "budget": context.budget,
                            "max_distance_meters": context.max_distance_meters,
                            "transport_mode": context.transport_mode,
                            "special_request": context.special_request,
                        },
                    },
                    "restaurant_json": restaurant,
                    "score": score,
                    "why": self._build_explanation(restaurant["name"], matched_traits, caution_traits),
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
        for payload in ranked_payloads:
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
    ) -> list[dict[str, Any]]:
        fake_candidates = build_mock_recommendation_candidates(
            destination_city=location.city,
            destination_country="",
        )
        try:
            google_candidates = self.google_places_client.search_restaurants(
                city=location.city,
                country="",
                lat=location.lat,
                lon=location.lon,
                radius_meters=context.max_distance_meters,
            )
        except Exception:
            return fake_candidates

        if not google_candidates:
            return fake_candidates
        if len(google_candidates) >= 5:
            return google_candidates[:5]

        existing_names = {
            candidate["restaurant_json"]["name"] for candidate in google_candidates
        }
        supplemental = [
            candidate
            for candidate in fake_candidates
            if candidate["restaurant_json"]["name"] not in existing_names
        ]
        return (google_candidates + supplemental)[:5]
