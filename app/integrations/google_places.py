import logging
import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.restaurant_identity import infer_restaurant_identity


logger = logging.getLogger(__name__)

IRRELEVANT_TYPES = {
    "convenience_store",
    "gas_station",
    "grocery_or_supermarket",
    "liquor_store",
    "pharmacy",
    "shopping_mall",
    "supermarket",
}
BASE_IGNORED_TYPES = {"food", "point_of_interest", "establishment", "store"}
DINNER_DOWNRANK_TYPES = {"bakery", "cafe", "meal_delivery", "meal_takeaway"}
DRINKS_FRIENDLY_TYPES = {"bar", "night_club"}
RESTAURANT_TYPES = {
    "restaurant",
    "seafood_restaurant",
    "steak_house",
    "pizza_restaurant",
    "meal_takeaway",
    "meal_delivery",
}
LUNCH_FRIENDLY_TYPES = RESTAURANT_TYPES | {"cafe", "bakery"}
SNACK_KEYWORDS = {
    "bakery",
    "boba",
    "bubble tea",
    "coffee",
    "cookie",
    "dessert",
    "donut",
    "gelato",
    "ice cream",
    "pastry",
    "tea",
}
DRINKS_KEYWORDS = {"bar", "brewery", "cocktail", "taproom", "wine"}
CUISINE_TYPE_MAP = {
    "restaurant": "restaurant",
    "seafood_restaurant": "seafood",
    "bar": "bar",
    "cafe": "cafe",
    "bakery": "bakery",
}


def _price_level_to_symbol(price_level: int | None) -> str:
    if not price_level:
        return "$$"
    return "$" * max(1, min(price_level, 4))


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _normalize_name_for_dedupe(name: str) -> str:
    cleaned = _normalize_text(name)
    tokens = [token for token in cleaned.split() if token not in {"restaurant", "restaurante", "cafe", "bar", "the"}]
    return " ".join(tokens)


def _normalize_address_for_dedupe(address: str) -> str:
    cleaned = _normalize_text(address)
    replacements = {
        " avenida ": " ave ",
        " av ": " ave ",
        " street ": " st ",
        " st ": " st ",
        " road ": " rd ",
        " rd ": " rd ",
    }
    padded = f" {cleaned} "
    for source, target in replacements.items():
        padded = padded.replace(source, target)
    return padded.strip()


def _extract_address(place: dict[str, Any]) -> str:
    return str(place.get("vicinity") or place.get("formatted_address") or "").strip()


def _extract_coordinates(place: dict[str, Any]) -> tuple[float | None, float | None]:
    location = place.get("geometry", {}).get("location", {})
    lat = location.get("lat")
    lon = location.get("lng")
    return (float(lat), float(lon)) if lat is not None and lon is not None else (None, None)


def _country_from_address(address: str) -> str:
    if not address or "," not in address:
        return ""
    return address.split(",")[-1].strip()


def _meal_relevance(place: dict[str, Any], meal_type: str | None) -> tuple[bool, float]:
    meal = (meal_type or "dinner").lower()
    raw_types = {str(item) for item in place.get("types", [])}
    name = _normalize_text(str(place.get("name") or ""))

    if raw_types & IRRELEVANT_TYPES:
        return False, 0.0

    if any(keyword in name for keyword in SNACK_KEYWORDS) and "restaurant" not in raw_types and "bar" not in raw_types:
        return False, 0.0

    score = 0.0
    if raw_types & RESTAURANT_TYPES:
        score += 1.2
    if "restaurant" in raw_types:
        score += 0.8

    if meal == "dinner":
        if raw_types & DINNER_DOWNRANK_TYPES and "restaurant" not in raw_types:
            score -= 1.6
        if any(keyword in name for keyword in SNACK_KEYWORDS):
            score -= 1.2
    elif meal == "lunch":
        if raw_types & LUNCH_FRIENDLY_TYPES:
            score += 0.5
        if "cafe" in raw_types or "bakery" in raw_types:
            score += 0.3
    elif meal == "drinks":
        if raw_types & DRINKS_FRIENDLY_TYPES:
            score += 1.5
        if any(keyword in name for keyword in DRINKS_KEYWORDS):
            score += 1.0
        if "restaurant" in raw_types and not (raw_types & DRINKS_FRIENDLY_TYPES):
            score -= 0.4
    return score > 0.2, score


def _passes_quality_threshold(place: dict[str, Any], relevance_score: float) -> bool:
    rating = float(place.get("rating") or 0)
    reviews = int(place.get("user_ratings_total") or 0)

    if reviews < 5:
        return False
    if rating and rating < 3.8 and reviews < 80:
        return False
    if reviews < 20 and not (rating >= 4.6 and relevance_score >= 1.2):
        return False
    return True


def _normalize_cuisine_tags(place: dict[str, Any]) -> list[str]:
    raw_types = [str(item) for item in place.get("types", [])]
    name = _normalize_text(str(place.get("name") or ""))
    tags: list[str] = []

    for place_type in raw_types:
        mapped = CUISINE_TYPE_MAP.get(place_type)
        if mapped and mapped not in tags:
            tags.append(mapped)

    keyword_map = {
        "seafood": "seafood",
        "tapas": "tapas",
        "wine": "wine_bar",
        "cocktail": "cocktail_bar",
        "dessert": "dessert",
        "bakery": "bakery",
        "cafe": "cafe",
    }
    for keyword, tag in keyword_map.items():
        if keyword in name and tag not in tags:
            tags.append(tag)

    if "bar" in raw_types and "bar" not in tags:
        tags.append("bar")
    if "restaurant" in raw_types and "restaurant" not in tags:
        tags.append("restaurant")
    if "strong food identity" not in tags and ("restaurant" in raw_types or "seafood" in tags or "tapas" in tags):
        tags.append("strong food identity")
    return tags[:5]


def _tourist_profile(place: dict[str, Any], relevance_score: float) -> str:
    reviews = int(place.get("user_ratings_total") or 0)
    rating = float(place.get("rating") or 0)
    raw_types = {str(item) for item in place.get("types", [])}

    if reviews >= 250 and rating < 4.4 and "restaurant" in raw_types:
        return "destination"
    if rating >= 4.4 and relevance_score >= 1.0:
        return "local-leaning"
    return "mixed"


def _normalize_vibe_tags(place: dict[str, Any], relevance_score: float) -> list[str]:
    tags: list[str] = []
    rating = float(place.get("rating") or 0)
    reviews = int(place.get("user_ratings_total") or 0)
    price_level = int(place.get("price_level") or 0)
    raw_types = {str(item) for item in place.get("types", [])}
    name = _normalize_text(str(place.get("name") or ""))

    if rating >= 4.5 and reviews >= 50:
        tags.append("local-favorite")
    if rating >= 4.3 and reviews >= 80:
        tags.append("authentic")
    if price_level <= 2:
        tags.extend(["casual", "grounded"])
    if price_level == 3:
        tags.append("stylish")
    if price_level >= 4:
        tags.extend(["refined", "upscale"])
    if reviews >= 120:
        tags.append("lively")
    if "bar" in raw_types:
        tags.append("shared-plates")
    if "meal_takeaway" not in raw_types and "bakery" not in raw_types:
        tags.append("warm")
    if "wine" in name:
        tags.append("stylish")
    if relevance_score >= 1.6 and "restaurant" in raw_types:
        tags.append("neighborhood")

    deduped: list[str] = []
    for tag in tags:
        normalized = tag.replace("_", "-")
        if normalized not in deduped:
            deduped.append(normalized)
    return deduped[:6]


def _formality_score(place: dict[str, Any], vibe_tags: list[str], cuisine_tags: list[str]) -> float:
    score = 0.18
    price_level = int(place.get("price_level") or 0)
    raw_types = {str(item) for item in place.get("types", [])}
    score += min(price_level * 0.12, 0.45)
    if "refined" in vibe_tags or "upscale" in vibe_tags:
        score += 0.22
    if "stylish" in vibe_tags:
        score += 0.08
    if "bar" in raw_types:
        score -= 0.08
    if "casual" in vibe_tags or "shared-plates" in vibe_tags:
        score -= 0.14
    if "meal_takeaway" in raw_types or "cafe" in raw_types or "bakery" in raw_types:
        score -= 0.12
    if "strong food identity" in cuisine_tags:
        score += 0.04
    return round(max(0.05, min(score, 0.98)), 2)


def _dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            float(item["restaurant_json"].get("rating") or 0),
            int(item["restaurant_json"].get("user_ratings_total") or 0),
        ),
        reverse=True,
    ):
        restaurant = candidate["restaurant_json"]
        key = " | ".join(
            [
                _normalize_name_for_dedupe(str(restaurant.get("name") or "")),
                _normalize_address_for_dedupe(str(restaurant.get("address") or "")),
            ]
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


def normalize_google_place(
    place: dict[str, Any],
    *,
    requested_city: str,
    requested_country: str,
    relevance_score: float,
) -> dict[str, Any]:
    address = _extract_address(place)
    lat, lon = _extract_coordinates(place)
    cuisine_tags = _normalize_cuisine_tags(place)
    vibe_tags = _normalize_vibe_tags(place, relevance_score)
    raw_types = [str(item) for item in place.get("types", [])]
    country = requested_country or _country_from_address(address)
    identity = infer_restaurant_identity(
        name=str(place.get("name") or ""),
        raw_types=raw_types,
        cuisine_tags=cuisine_tags,
        vibe_tags=vibe_tags,
        food_style_tags=["strong_food_identity" if "strong food identity" in cuisine_tags else ""],
        price_level=_price_level_to_symbol(place.get("price_level")),
        formality_score=_formality_score(place, vibe_tags, cuisine_tags),
        tourist_profile=_tourist_profile(place, relevance_score),
        rating=float(place.get("rating") or 0) or None,
        user_ratings_total=int(place.get("user_ratings_total") or 0),
        text_blobs=[address],
    )

    return {
        "restaurant_json": {
            "name": place.get("name", f"{requested_city} Restaurant"),
            "city": requested_city,
            "country": country,
            "address": address or None,
            "lat": lat,
            "lon": lon,
            "source": "google_places",
            "price_level": _price_level_to_symbol(place.get("price_level")),
            "rating": float(place.get("rating") or 0) or None,
            "user_ratings_total": int(place.get("user_ratings_total") or 0),
            "raw_types": raw_types,
            "cuisine_tags": cuisine_tags,
            "vibe_tags": vibe_tags,
            "formality_score": _formality_score(place, vibe_tags, cuisine_tags),
            "tourist_profile": _tourist_profile(place, relevance_score),
            "google_place_id": place.get("place_id"),
            "primary_archetype": identity["primary_archetype"],
            "secondary_archetypes": identity["secondary_archetypes"],
            "positive_traits": identity["positive_traits"],
            "negative_traits": identity["negative_traits"],
            "character_score": identity["character_score"],
            "localness_score": identity["localness_score"],
            "food_identity_score": identity["food_identity_score"],
        }
    }


def normalize_seed_place_candidate(
    place: dict[str, Any],
    *,
    requested_city: str,
) -> dict[str, Any]:
    address = _extract_address(place)
    lat, lon = _extract_coordinates(place)
    raw_types = [str(item) for item in place.get("types", [])]
    relevance_score = 1.4 if "restaurant" in raw_types else 1.0
    cuisine_tags = _normalize_cuisine_tags(place)
    vibe_tags = _normalize_vibe_tags(place, relevance_score)
    rating = float(place.get("rating") or 0) or None
    user_ratings_total = int(place.get("user_ratings_total") or 0) or None
    price_level = _price_level_to_symbol(place.get("price_level"))
    tourist_profile = _tourist_profile(place, relevance_score)
    formality_score = _formality_score(place, vibe_tags, cuisine_tags)
    identity = infer_restaurant_identity(
        name=str(place.get("name") or ""),
        raw_types=raw_types,
        cuisine_tags=cuisine_tags,
        vibe_tags=vibe_tags,
        food_style_tags=[
            value
            for value in [
                "strong_food_identity" if "strong food identity" in cuisine_tags else "",
                "creative" if "creative" in cuisine_tags else "",
            ]
            if value
        ],
        price_level=price_level,
        formality_score=formality_score,
        tourist_profile=tourist_profile,
        rating=rating,
        user_ratings_total=user_ratings_total,
        text_blobs=[address],
    )
    menu_summary_text = ", ".join(tag.replace("_", " ") for tag in cuisine_tags if tag != "restaurant") or None
    review_summary_text = (
        f"Rated {rating:.1f} from {user_ratings_total} reviews with a {'local-leaning' if tourist_profile == 'local-leaning' else tourist_profile} profile."
        if rating is not None and user_ratings_total is not None
        else None
    )
    editorial_summary_text = (
        f"{' / '.join(vibe_tags[:3]).replace('-', ' ')} place with {' / '.join(cuisine_tags[:2]).replace('_', ' ')} cues."
        if vibe_tags or cuisine_tags
        else None
    )
    return {
        "name": str(place.get("name") or "").strip() or f"{requested_city} Restaurant",
        "city": requested_city,
        "formatted_address": address or None,
        "source": "google_places",
        "source_place_id": str(place.get("place_id") or ""),
        "lat": lat,
        "lon": lon,
        "price_level": price_level,
        "rating": rating,
        "user_ratings_total": user_ratings_total,
        "raw_types": raw_types,
        "review_summary_text": review_summary_text,
        "editorial_summary_text": editorial_summary_text,
        "menu_summary_text": menu_summary_text,
        "raw_seed_note_text": None,
        "raw_place_metadata_json": {
            "name": place.get("name"),
            "city": requested_city,
            "formatted_address": address or None,
            "price_level": price_level,
            "rating": rating,
            "user_ratings_total": user_ratings_total,
            "raw_types": raw_types,
        },
        "raw_review_text": review_summary_text,
        "derived_traits_json": {
            "vibe": vibe_tags,
            "formality": ["formal" if formality_score >= 0.68 else "casual" if formality_score <= 0.35 else "casual_polished"],
            "food_style": [
                value
                for value in [
                    "strong_food_identity" if "strong food identity" in cuisine_tags else None,
                    "creative" if "creative" in cuisine_tags else None,
                ]
                if value is not None
            ],
            "social_feel": [tourist_profile.replace("-", "_")],
            "use_case": ["groups"] if "shared-plates" in vibe_tags else ["everyday"],
            "cuisine_style": [tag.replace("-", "_") for tag in cuisine_tags if tag != "restaurant"],
            "primary_archetype": identity["primary_archetype"],
            "secondary_archetypes": identity["secondary_archetypes"],
            "positive_traits": identity["positive_traits"],
            "negative_traits": identity["negative_traits"],
            "confidence_score": identity["confidence_score"],
        },
        "ai_summary_text": None,
        "place_traits_json": {
            "vibe": vibe_tags,
            "food_style": cuisine_tags,
            "tourist_tolerance": [f"{tourist_profile} places"],
            "price_band": price_level,
            "likely_formality": "formal" if formality_score >= 0.68 else "casual" if formality_score <= 0.35 else "balanced",
            "formality_score": formality_score,
            "tourist_profile": tourist_profile,
            "primary_archetype": identity["primary_archetype"],
            "secondary_archetypes": identity["secondary_archetypes"],
            "positive_traits": identity["positive_traits"],
            "negative_traits": identity["negative_traits"],
            "character_score": identity["character_score"],
            "localness_score": identity["localness_score"],
            "food_identity_score": identity["food_identity_score"],
        },
    }


class GooglePlacesClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def geocode_city(
        self,
        *,
        city: str,
        country: str,
    ) -> tuple[float, float] | None:
        if not self.settings.google_places_api_key:
            return None

        query = city if not country else f"{city}, {country}"
        response = httpx.get(
            self.settings.google_geocoding_base_url,
            params={
                "key": self.settings.google_places_api_key,
                "address": query,
            },
            timeout=self.settings.google_places_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in {"OK", "ZERO_RESULTS"}:
            raise RuntimeError(payload.get("error_message") or payload.get("status") or "Google geocoding request failed")

        results = payload.get("results", [])
        if not results:
            return None

        location = results[0].get("geometry", {}).get("location", {})
        lat = location.get("lat")
        lon = location.get("lng")
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)

    def search_restaurants(
        self,
        *,
        city: str,
        country: str,
        lat: float | None,
        lon: float | None,
        radius_meters: int | None,
        meal_type: str | None = None,
    ) -> list[dict[str, Any]]:
        if not self.settings.google_places_api_key or lat is None or lon is None or radius_meters is None:
            logger.debug(
                "Google Places skipped city=%s meal_type=%s has_key=%s has_coords=%s has_radius=%s",
                city,
                meal_type,
                bool(self.settings.google_places_api_key),
                lat is not None and lon is not None,
                radius_meters is not None,
            )
            return []

        response = httpx.get(
            self.settings.google_places_base_url,
            params={
                "key": self.settings.google_places_api_key,
                "location": f"{lat},{lon}",
                "radius": radius_meters,
                "type": "restaurant",
                "keyword": city,
            },
            timeout=self.settings.google_places_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in {"OK", "ZERO_RESULTS"}:
            raise RuntimeError(payload.get("error_message") or payload.get("status") or "Google Places request failed")

        raw_results = payload.get("results", [])
        candidates: list[dict[str, Any]] = []
        for place in raw_results:
            if not place.get("name"):
                continue
            is_relevant, relevance_score = _meal_relevance(place, meal_type)
            if not is_relevant:
                continue
            if not _passes_quality_threshold(place, relevance_score):
                continue
            candidates.append(
                normalize_google_place(
                    place,
                    requested_city=city,
                    requested_country=country,
                    relevance_score=relevance_score,
                )
            )

        deduped = _dedupe_candidates(candidates)
        logger.debug(
            "Google Places candidate filtering city=%s meal_type=%s raw=%s kept=%s",
            city,
            meal_type,
            len(raw_results),
            len(deduped),
        )
        return deduped[:10]

    def search_seed_places(
        self,
        *,
        name: str,
        city: str,
    ) -> list[dict[str, Any]]:
        if not self.settings.google_places_api_key:
            logger.debug("Google seed search skipped city=%s has_key=%s", city, False)
            return []

        response = httpx.get(
            self.settings.google_places_text_search_base_url,
            params={
                "key": self.settings.google_places_api_key,
                "query": f"{name} {city}",
                "type": "restaurant",
            },
            timeout=self.settings.google_places_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in {"OK", "ZERO_RESULTS"}:
            raise RuntimeError(payload.get("error_message") or payload.get("status") or "Google Places seed search failed")

        raw_results = payload.get("results", [])
        candidates: list[dict[str, Any]] = []
        for place in raw_results:
            raw_types = {str(item) for item in place.get("types", [])}
            if not place.get("name") or raw_types & IRRELEVANT_TYPES:
                continue
            if "restaurant" not in raw_types and "bar" not in raw_types and "cafe" not in raw_types:
                continue
            normalized = normalize_seed_place_candidate(place, requested_city=city)
            if not normalized["source_place_id"]:
                continue
            candidates.append(normalized)

        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = " | ".join(
                [
                    _normalize_name_for_dedupe(candidate["name"]),
                    _normalize_address_for_dedupe(candidate.get("formatted_address") or ""),
                ]
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)

        logger.debug(
            "Google seed search city=%s query=%s raw=%s kept=%s",
            city,
            name,
            len(raw_results),
            len(deduped),
        )
        return deduped[:5]
