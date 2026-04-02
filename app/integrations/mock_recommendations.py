from typing import Any


def build_mock_recommendation(
    *,
    destination_city: str,
    destination_country: str,
    top_cities: list[str],
    loved_restaurants: list[str],
) -> dict[str, Any]:
    return {
        "request_context_json": {
            "destination_city": destination_city,
            "destination_country": destination_country,
            "signals_used": {
                "top_cities": top_cities,
                "loved_restaurants": loved_restaurants,
            },
        },
        "restaurant_json": {
            "name": f"{destination_city} Atelier",
            "city": destination_city,
            "country": destination_country,
            "cuisine": "Contemporary local",
            "price_tier": "$$$",
        },
        "score": 0.91,
        "why": (
            f"Selected for travelers heading to {destination_city} who respond well to destination-led dining "
            f"signals and chef-driven rooms."
        ),
        "anchors_json": {
            "matched_cities": top_cities,
            "matched_seed_restaurants": loved_restaurants,
        },
    }
