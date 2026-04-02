def build_mock_recommendations(*, destination_city: str, destination_country: str, taste_vibe: str, cuisines: list[str]) -> dict:
    primary_cuisine = cuisines[0] if cuisines else "regional"
    summary = (
        f"A short-list for {destination_city}, {destination_country} tuned for a {taste_vibe.lower()} "
        f"with a bias toward {primary_cuisine} dining."
    )
    items = [
        {
            "restaurant_name": f"{destination_city} Market Table",
            "neighborhood": "Old Town",
            "cuisine": primary_cuisine.title(),
            "why_it_matches": "A polished local favorite with a focused menu and strong ingredient sourcing.",
            "price_tier": "$$",
        },
        {
            "restaurant_name": f"{destination_city} Night Counter",
            "neighborhood": "River District",
            "cuisine": "Contemporary Small Plates",
            "why_it_matches": "Fits travelers who want energetic service and a chef-driven room without a tasting-menu format.",
            "price_tier": "$$$",
        },
        {
            "restaurant_name": f"{destination_city} Corner Grill",
            "neighborhood": "Central Station",
            "cuisine": "Local Comfort Food",
            "why_it_matches": "A reliable first-night option with broad appeal and strong local signatures.",
            "price_tier": "$$",
        },
    ]
    return {"summary": summary, "items": items}
