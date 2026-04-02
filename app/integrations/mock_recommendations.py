from typing import Any


def build_mock_recommendations(
    *,
    destination_city: str,
    destination_country: str,
    dining_context: str | None,
    preferred_cities: list[str],
    preferred_keywords: list[str],
    loved_restaurants: list[str],
) -> list[dict[str, Any]]:
    names = [
        "Atelier One",
        "Counter Two",
        "Market House",
        "Late Table",
        "Garden Room",
    ]
    price_levels = ["$$$", "$$", "$$", "$", "$$$"]
    cuisine_sets = [
        ["seasonal", "tasting-menu"],
        ["small-plates", "regional"],
        ["market-driven", "seafood"],
        ["street-food", "casual"],
        ["bistro", "comfort-food"],
    ]
    vibe_sets = [
        ["chef-driven", "refined"],
        ["buzzing", "shared-plates"],
        ["local-favorite", "bright"],
        ["late-night", "energetic"],
        ["calm", "design-forward"],
    ]
    base_score = 0.94
    anchors = loved_restaurants[:3]
    city_signals = preferred_cities[:3]
    keyword_signals = preferred_keywords[:4]

    recommendations: list[dict[str, Any]] = []
    for index, suffix in enumerate(names, start=1):
        restaurant_name = f"{destination_city} {suffix}"
        recommendations.append(
            {
                "request_context_json": {
                    "destination_city": destination_city,
                    "destination_country": destination_country,
                    "dining_context": dining_context,
                    "signals_used": {
                        "preferred_cities": city_signals,
                        "preferred_keywords": keyword_signals,
                    },
                },
                "restaurant_json": {
                    "name": restaurant_name,
                    "city": destination_city,
                    "country": destination_country,
                    "price_level": price_levels[index - 1],
                    "cuisine_tags": cuisine_sets[index - 1],
                    "vibe_tags": vibe_sets[index - 1],
                },
                "score": round(base_score - ((index - 1) * 0.03), 2),
                "why": (
                    f"{restaurant_name} matches the user's preference for "
                    f"{', '.join(keyword_signals[:2]) or 'well-balanced'} dining in {destination_city}."
                ),
                "anchors_json": {
                    "seed_restaurants": anchors,
                    "matched_cities": city_signals,
                    "matched_keywords": keyword_signals,
                },
            }
        )

    return recommendations
