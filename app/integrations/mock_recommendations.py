from typing import Any


def build_mock_recommendation_candidates(
    *,
    destination_city: str,
    destination_country: str,
) -> list[dict[str, Any]]:
    return [
        {
            "restaurant_json": {
                "name": f"{destination_city} Atelier One",
                "city": destination_city,
                "country": destination_country,
                "source": "fallback_mock",
                "price_level": "$$$",
                "cuisine_tags": ["seasonal", "tasting-menu", "creative"],
                "vibe_tags": ["refined", "stylish", "chef-driven"],
                "formality_score": 0.95,
                "tourist_profile": "destination",
            }
        },
        {
            "restaurant_json": {
                "name": f"{destination_city} Counter Two",
                "city": destination_city,
                "country": destination_country,
                "source": "fallback_mock",
                "price_level": "$$",
                "cuisine_tags": ["small-plates", "creative", "strong food identity"],
                "vibe_tags": ["lively", "shared-plates", "stylish", "casual"],
                "formality_score": 0.25,
                "tourist_profile": "local-leaning",
            }
        },
        {
            "restaurant_json": {
                "name": f"{destination_city} Market House",
                "city": destination_city,
                "country": destination_country,
                "source": "fallback_mock",
                "price_level": "$$",
                "cuisine_tags": ["market-driven", "strong food identity", "regional"],
                "vibe_tags": ["local-favorite", "grounded", "authentic", "warm", "neighborhood"],
                "formality_score": 0.2,
                "tourist_profile": "local-leaning",
            }
        },
        {
            "restaurant_json": {
                "name": f"{destination_city} Late Table",
                "city": destination_city,
                "country": destination_country,
                "source": "fallback_mock",
                "price_level": "$",
                "cuisine_tags": ["casual", "street-food", "shared-plates"],
                "vibe_tags": ["lively", "casual", "energetic"],
                "formality_score": 0.1,
                "tourist_profile": "mixed",
            }
        },
        {
            "restaurant_json": {
                "name": f"{destination_city} Garden Room",
                "city": destination_city,
                "country": destination_country,
                "source": "fallback_mock",
                "price_level": "$$$",
                "cuisine_tags": ["bistro", "creative"],
                "vibe_tags": ["warm", "stylish", "refined"],
                "formality_score": 0.65,
                "tourist_profile": "mixed",
            }
        },
        {
            "restaurant_json": {
                "name": f"{destination_city} Corner Kitchen",
                "city": destination_city,
                "country": destination_country,
                "source": "fallback_mock",
                "price_level": "$$",
                "cuisine_tags": ["regional", "comfort_food", "strong food identity"],
                "vibe_tags": ["warm", "casual", "local-favorite", "grounded"],
                "formality_score": 0.18,
                "tourist_profile": "local-leaning",
            }
        },
        {
            "restaurant_json": {
                "name": f"{destination_city} Wine Lane",
                "city": destination_city,
                "country": destination_country,
                "source": "fallback_mock",
                "price_level": "$$",
                "cuisine_tags": ["small-plates", "wine-bar", "creative"],
                "vibe_tags": ["stylish", "lively", "casual"],
                "formality_score": 0.35,
                "tourist_profile": "mixed",
            }
        },
        {
            "restaurant_json": {
                "name": f"{destination_city} Harbor Plates",
                "city": destination_city,
                "country": destination_country,
                "source": "fallback_mock",
                "price_level": "$$$",
                "cuisine_tags": ["seafood", "regional", "strong food identity"],
                "vibe_tags": ["buzzy", "warm", "shared-plates"],
                "formality_score": 0.4,
                "tourist_profile": "mixed",
            }
        },
        {
            "restaurant_json": {
                "name": f"{destination_city} Night Counter",
                "city": destination_city,
                "country": destination_country,
                "source": "fallback_mock",
                "price_level": "$",
                "cuisine_tags": ["street-food", "regional", "casual"],
                "vibe_tags": ["energetic", "casual", "local-favorite"],
                "formality_score": 0.08,
                "tourist_profile": "local-leaning",
            }
        },
    ]
