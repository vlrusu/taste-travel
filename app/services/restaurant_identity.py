from __future__ import annotations

from typing import Any


LOCAL_ARCHETYPES = {
    "neighborhood_wine_bar",
    "chef_driven_small_plates",
    "polished_local_bistro",
    "design_forward_casual",
    "everyday_neighborhood_spot",
    "local_institution",
}

CORPORATE_ARCHETYPES = {
    "corporate_seafood_steak",
    "hotel_adjacent_upscale",
    "business_district_dining",
    "tourist_favorite",
}


def _append_unique(target: list[str], *values: str) -> None:
    for value in values:
        if value and value not in target:
            target.append(value)


def infer_restaurant_identity(
    *,
    name: str,
    raw_types: list[str] | None = None,
    cuisine_tags: list[str] | None = None,
    vibe_tags: list[str] | None = None,
    food_style_tags: list[str] | None = None,
    price_level: str | None = None,
    formality_score: float | None = None,
    tourist_profile: str | None = None,
    rating: float | None = None,
    user_ratings_total: int | None = None,
    text_blobs: list[str | None] | None = None,
) -> dict[str, Any]:
    raw_types_set = {str(value) for value in (raw_types or [])}
    cuisine_set = {str(value) for value in (cuisine_tags or [])}
    vibe_set = {str(value) for value in (vibe_tags or [])}
    food_style_set = {str(value) for value in (food_style_tags or [])}
    text = " ".join(value.lower() for value in (text_blobs or []) if value).strip()
    name_lower = (name or "").lower()
    price_band = len(price_level or "")
    formality = formality_score or 0.0
    reviews = user_ratings_total or 0
    tourist = tourist_profile or "mixed"

    positive_traits: list[str] = []
    negative_traits: list[str] = []
    secondary_archetypes: list[str] = []

    if tourist == "local-leaning":
        _append_unique(positive_traits, "local_leaning", "neighborhood_favorite")
    if "warm" in vibe_set:
        _append_unique(positive_traits, "warm")
    if {"grounded", "authentic", "local-favorite", "neighborhood"} & vibe_set:
        _append_unique(positive_traits, "grounded", "characterful", "unpretentious")
    if {"strong food identity", "regional", "seafood", "small-plates", "small_plates", "market-driven"} & cuisine_set:
        _append_unique(positive_traits, "food_forward", "strong_food_identity")
    if {"chef_driven", "creative"} & food_style_set or {"chef-driven", "creative"} & vibe_set:
        _append_unique(positive_traits, "chef_driven", "food_forward")
    if {"regional", "tapas", "seafood", "bistro", "wine_bar", "wine-bar"} & cuisine_set:
        _append_unique(positive_traits, "culturally_specific")
    if reviews >= 40 and tourist != "destination" and formality <= 0.55:
        _append_unique(positive_traits, "independent")
    if price_band >= 3 and formality >= 0.62:
        _append_unique(positive_traits, "polished_luxury")
    if tourist == "destination" and price_band >= 3:
        _append_unique(positive_traits, "business_district", "safe_luxury")
    if "corporate" in negative_traits and price_band >= 3:
        _append_unique(positive_traits, "luxury_consistency")

    if tourist == "destination":
        _append_unique(negative_traits, "tourist_heavy", "business_district")
    if price_band >= 3 and formality >= 0.7:
        _append_unique(negative_traits, "overly_formal")
    if (
        price_band >= 3
        and tourist == "destination"
        and ({"refined", "upscale", "stylish"} & vibe_set or "tasting-menu" in cuisine_set)
    ):
        _append_unique(negative_traits, "generic_upscale", "safe_luxury")
    if any(token in name_lower for token in ["prime", "grill", "chophouse", "club", "steak", "seafood"]) and price_band >= 3:
        _append_unique(negative_traits, "corporate", "generic_upscale")
    if "hotel" in text or "lobby" in text:
        _append_unique(negative_traits, "hotel_restaurant_feel", "convention_dining")
    if "business district" in text or "downtown" in text:
        _append_unique(negative_traits, "business_district", "convention_dining")
    if "chain" in text:
        _append_unique(negative_traits, "chain_feeling")
    if "scene" in text and "food" not in text:
        _append_unique(negative_traits, "sceney_without_substance")

    primary_archetype = "everyday_neighborhood_spot"
    if (
        {"wine_bar", "wine-bar"} & cuisine_set
        or ("bar" in raw_types_set and {"small_plates", "small-plates"} & cuisine_set)
    ) and tourist != "destination":
        primary_archetype = "neighborhood_wine_bar"
    elif (
        ({"small_plates", "small-plates"} & cuisine_set or {"chef-driven", "chef_driven"} & (vibe_set | food_style_set))
        and tourist != "destination"
    ):
        primary_archetype = "chef_driven_small_plates"
    elif "bistro" in cuisine_set and tourist == "local-leaning":
        primary_archetype = "polished_local_bistro"
    elif {"refined", "upscale"} & vibe_set and "tasting-menu" in cuisine_set:
        primary_archetype = "destination_tasting_room"
    elif (
        ("steak_house" in raw_types_set or "seafood_restaurant" in raw_types_set or "seafood" in cuisine_set)
        and price_band >= 3
        and tourist == "destination"
    ) or "corporate" in negative_traits:
        primary_archetype = "corporate_seafood_steak"
    elif "hotel_restaurant_feel" in negative_traits:
        primary_archetype = "hotel_adjacent_upscale"
    elif "stylish" in vibe_set and "casual" in vibe_set and tourist != "destination":
        primary_archetype = "design_forward_casual"
    elif tourist == "destination" and "business_district" in negative_traits:
        primary_archetype = "business_district_dining"
    elif tourist == "destination":
        primary_archetype = "tourist_favorite"
    elif reviews >= 250 and rating and rating >= 4.4 and tourist == "local-leaning":
        primary_archetype = "local_institution"

    if primary_archetype != "everyday_neighborhood_spot" and tourist == "local-leaning":
        _append_unique(secondary_archetypes, "everyday_neighborhood_spot")
    if "stylish" in vibe_set and price_band <= 2:
        _append_unique(secondary_archetypes, "design_forward_casual")
    if tourist == "destination" and "safe_luxury" in negative_traits:
        _append_unique(secondary_archetypes, "business_district_dining")

    character_score = 0.1
    if {"characterful", "independent", "grounded", "unpretentious"} & set(positive_traits):
        character_score += 0.45
    if primary_archetype in LOCAL_ARCHETYPES:
        character_score += 0.2
    if {"generic_upscale", "corporate", "safe_luxury"} & set(negative_traits):
        character_score -= 0.22

    localness_score = 0.1
    if tourist == "local-leaning":
        localness_score += 0.5
    elif tourist == "mixed":
        localness_score += 0.15
    if primary_archetype in LOCAL_ARCHETYPES:
        localness_score += 0.15
    if {"tourist_heavy", "business_district", "convention_dining"} & set(negative_traits):
        localness_score -= 0.25

    food_identity_score = 0.12
    if {"food_forward", "strong_food_identity", "chef_driven", "culturally_specific"} & set(positive_traits):
        food_identity_score += 0.48
    if primary_archetype in {"chef_driven_small_plates", "polished_local_bistro", "local_institution"}:
        food_identity_score += 0.12
    if "sceney_without_substance" in negative_traits:
        food_identity_score -= 0.18

    return {
        "primary_archetype": primary_archetype,
        "secondary_archetypes": secondary_archetypes,
        "positive_traits": positive_traits,
        "negative_traits": negative_traits,
        "character_score": round(max(0.0, min(character_score, 1.0)), 2),
        "localness_score": round(max(0.0, min(localness_score, 1.0)), 2),
        "food_identity_score": round(max(0.0, min(food_identity_score, 1.0)), 2),
        "confidence_score": 0.78 if text or raw_types_set else 0.45,
    }
