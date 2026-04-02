def test_health_check(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_and_patch_me(client):
    get_response = client.get("/api/v1/me")

    assert get_response.status_code == 200
    assert get_response.json()["email"] == "demo@tastetravel.app"

    patch_response = client.patch(
        "/api/v1/me",
        json={
            "email": "alex@example.com",
            "home_city": "Chicago",
            "onboarding_complete": True,
        },
    )

    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["email"] == "alex@example.com"
    assert body["home_city"] == "Chicago"
    assert body["onboarding_complete"] is True


def test_seed_crud_and_taste_profile_generation(client):
    create_response = client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Tokyo ramen counters",
            "city": "Tokyo",
            "sentiment": "love",
            "notes": "Late-night spots with short menus",
        },
    )

    assert create_response.status_code == 201
    seed_id = create_response.json()["id"]

    list_response = client.get("/api/v1/me/seeds")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    profile_response = client.post("/api/v1/me/taste-profile:generate")
    assert profile_response.status_code == 200
    profile = profile_response.json()["taste_profile"]
    assert profile["attributes_json"]["loved_restaurants"] == ["Tokyo ramen counters"]
    assert "Tokyo" in profile["summary"]
    assert profile["attributes_json"]["default_profile"] is False
    assert "vibe" in profile["attributes_json"]
    assert "food_style" in profile["attributes_json"]
    assert "service_style" in profile["attributes_json"]
    assert "avoid" in profile["attributes_json"]
    assert "tourist_tolerance" in profile["attributes_json"]
    assert "novelty_preference" in profile["attributes_json"]

    fetch_profile_response = client.get("/api/v1/me/taste-profile")
    assert fetch_profile_response.status_code == 200
    assert fetch_profile_response.json()["id"] == profile["id"]

    delete_response = client.delete(f"/api/v1/me/seeds/{seed_id}")
    assert delete_response.status_code == 204


def test_duplicate_seed_restaurant_is_rejected(client):
    payload = {
        "name": "Tokyo ramen counters",
        "city": "Tokyo",
        "sentiment": "love",
        "notes": "Late-night spots with short menus",
    }

    first_response = client.post("/api/v1/me/seeds", json=payload)
    duplicate_response = client.post("/api/v1/me/seeds", json=payload)

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "A seed restaurant with that name and city already exists"
    }


def test_recommendation_generation_retrieval_and_feedback(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Basque tasting rooms",
            "city": "San Sebastian",
            "sentiment": "love",
            "notes": "Menus with local seafood and low-intervention wine",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    generate_response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {
                "city": "San Sebastian",
                "lat": 43.3183,
                "lon": -1.9812,
            },
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "not too formal, more local than touristy",
            },
        },
    )

    assert generate_response.status_code == 201
    recommendations = generate_response.json()["recommendations"]
    assert len(recommendations) == 5
    recommendation = recommendations[0]
    recommendation_id = recommendation["id"]
    assert recommendation["request_context_json"]["location"]["city"] == "San Sebastian"
    assert recommendation["request_context_json"]["context"]["budget"] == "$$"
    assert recommendation["request_context_json"]["context"]["special_request"] == "not too formal, more local than touristy"
    assert recommendation["restaurant_json"]["city"] == "San Sebastian"
    assert recommendation["restaurant_json"]["name"] == "San Sebastian Market House"
    assert recommendation["restaurant_json"]["price_level"] == "$$"
    assert "Basque tasting rooms" in recommendation["anchors_json"]["seed_restaurants"]
    assert "local feel" in recommendation["why"] or "warm neighborhood vibe" in recommendation["why"]

    get_response = client.get(f"/api/v1/recommendations/{recommendation_id}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == recommendation_id

    feedback_response = client.post(
        f"/api/v1/recommendations/{recommendation_id}/feedback",
        json={"feedback_type": "perfect", "notes": "Strong first-pass shortlist"},
    )

    assert feedback_response.status_code == 200
    feedback_body = feedback_response.json()
    assert feedback_body["feedback_type"] == "perfect"
    assert feedback_body["notes"] == "Strong first-pass shortlist"
    assert feedback_body["created_at"] is not None


def test_less_formal_places_rank_above_tasting_menu_for_anti_stuffy_profile(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Warm Local Spot",
            "city": "Barcelona",
            "sentiment": "love",
            "notes": "warm, neighborhood feel, not stuffy, feels real",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Barcelona", "lat": 41.3874, "lon": 2.1686},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "not too formal",
            },
        },
    )

    assert response.status_code == 201
    recommendations = response.json()["recommendations"]
    top_names = [item["restaurant_json"]["name"] for item in recommendations[:2]]
    assert f"Barcelona Atelier One" not in top_names
    assert recommendations[0]["restaurant_json"]["name"] in {
        "Barcelona Market House",
        "Barcelona Counter Two",
    }


def test_budget_preference_ranks_dollar_match_above_more_expensive_option(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Creative Corner",
            "city": "Portland",
            "sentiment": "love",
            "notes": "creative, lively, neighborhood feel",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Portland", "lat": 45.5152, "lon": -122.6784},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": None,
            },
        },
    )

    assert response.status_code == 201
    recommendations = response.json()["recommendations"]
    names = [item["restaurant_json"]["name"] for item in recommendations]
    assert names.index("Portland Counter Two") < names.index("Portland Garden Room")
    assert names.index("Portland Market House") < names.index("Portland Atelier One")


def test_recommendation_explanations_are_distinct_across_top_five(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Shared Plates Club",
            "city": "Mexico City",
            "sentiment": "love",
            "notes": "lively, stylish, strong food, neighborhood feel",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Mexico City", "lat": 19.4326, "lon": -99.1332},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "shared plates and local feel",
            },
        },
    )

    assert response.status_code == 201
    explanations = [item["why"] for item in response.json()["recommendations"]]
    assert len(set(explanations)) == 5


def test_budget_and_special_request_are_present_and_affect_scores(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Local Bistro",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "warm, neighborhood feel, not stuffy, strong food",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Lisbon", "lat": 38.7223, "lon": -9.1393},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "memorable but not too formal",
            },
        },
    )

    assert response.status_code == 201
    recommendations = response.json()["recommendations"]
    top = recommendations[0]
    bottom = recommendations[-1]
    assert top["request_context_json"]["context"]["budget"] == "$$"
    assert top["request_context_json"]["context"]["special_request"] == "memorable but not too formal"
    assert top["anchors_json"]["score_breakdown"]["budget_match_score"] > 0
    assert top["anchors_json"]["score_breakdown"]["special_request_score"] > 0
    assert bottom["anchors_json"]["score_breakdown"]["formality_penalty"] > 0
    assert top["restaurant_json"]["price_level"] == "$$"


def test_recommendations_fall_back_to_fake_catalog_when_places_lookup_fails(client, monkeypatch):
    from app.integrations.google_places import GooglePlacesClient

    def fail_lookup(self, *, city, country, lat, lon, radius_meters):
        raise RuntimeError("places unavailable")

    monkeypatch.setattr(GooglePlacesClient, "search_restaurants", fail_lookup)

    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Fallback Bistro",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "warm, neighborhood feel",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Lisbon", "lat": 38.7223, "lon": -9.1393},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "memorable but not too formal",
            },
        },
    )

    assert response.status_code == 201
    recommendations = response.json()["recommendations"]
    names = [item["restaurant_json"]["name"] for item in recommendations]
    assert "Lisbon Market House" in names
    assert all(item["restaurant_json"]["source"] == "fallback_mock" for item in recommendations)


def test_recommendations_geocode_city_when_lat_lon_are_missing(client, monkeypatch):
    from app.integrations.google_places import GooglePlacesClient

    seen: dict[str, object] = {}

    def fake_geocode(self, *, city, country):
        seen["city"] = city
        seen["country"] = country
        return 38.7223, -9.1393

    def fake_search(self, *, city, country, lat, lon, radius_meters):
        seen["search_city"] = city
        seen["lat"] = lat
        seen["lon"] = lon
        seen["radius_meters"] = radius_meters
        return [
            {
                "restaurant_json": {
                    "name": "Lisbon Real Place",
                    "city": city,
                    "country": "Portugal",
                    "source": "google_places",
                    "price_level": "$$",
                    "cuisine_tags": ["creative", "strong food identity"],
                    "vibe_tags": ["warm", "local-favorite", "grounded"],
                    "formality_score": 0.34,
                    "tourist_profile": "local-leaning",
                }
            }
        ]

    monkeypatch.setattr(GooglePlacesClient, "geocode_city", fake_geocode)
    monkeypatch.setattr(GooglePlacesClient, "search_restaurants", fake_search)

    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Local Bistro",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "warm, neighborhood feel, not stuffy, strong food",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Lisbon"},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "memorable but not too formal",
            },
        },
    )

    assert response.status_code == 201
    recommendations = response.json()["recommendations"]
    google_results = [
        item for item in recommendations if item["restaurant_json"]["source"] == "google_places"
    ]
    assert google_results
    assert google_results[0]["restaurant_json"]["name"] == "Lisbon Real Place"
    assert all(item["request_context_json"]["location"]["lat"] == 38.7223 for item in recommendations)
    assert all(item["request_context_json"]["location"]["lon"] == -9.1393 for item in recommendations)
    assert seen == {
        "city": "Lisbon",
        "country": "",
        "search_city": "Lisbon",
        "lat": 38.7223,
        "lon": -9.1393,
        "radius_meters": 2000,
    }


def test_taste_profile_generation_without_seeds_returns_default_profile(client):
    response = client.post("/api/v1/me/taste-profile:generate")

    assert response.status_code == 200
    profile = response.json()["taste_profile"]
    assert profile["attributes_json"]["default_profile"] is True
    assert profile["attributes_json"]["loved_restaurants"] == []
    assert profile["attributes_json"]["vibe"] == ["welcoming", "unfussy"]


def test_taste_profile_normalizes_warm_creative_neighborhood_not_stuffy(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Neighborhood Supper Club",
            "city": "Chicago",
            "sentiment": "love",
            "notes": "warm, creative, neighborhood feel, not stuffy",
        },
    )

    response = client.post("/api/v1/me/taste-profile:generate")

    assert response.status_code == 200
    attributes = response.json()["taste_profile"]["attributes_json"]
    assert "warm" in attributes["vibe"]
    assert "neighborhood" in attributes["vibe"]
    assert "local" in attributes["vibe"]
    assert "creative" in attributes["food_style"]
    assert "stuffy" in attributes["avoid"]
    assert "overly formal" in attributes["avoid"]


def test_taste_profile_normalizes_lively_stylish_strong_food_feels_real(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "City Corner Dining Room",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "lively, stylish, strong food, feels real",
        },
    )

    response = client.post("/api/v1/me/taste-profile:generate")

    assert response.status_code == 200
    payload = response.json()["taste_profile"]
    attributes = payload["attributes_json"]
    assert "lively" in attributes["vibe"]
    assert "stylish" in attributes["vibe"]
    assert "grounded" in attributes["vibe"]
    assert "authentic" in attributes["vibe"]
    assert "strong food identity" in attributes["food_style"]
    assert "food" not in attributes["preferred_keywords"]
    assert "feels" not in attributes["preferred_keywords"]
    assert "real" not in attributes["preferred_keywords"]
    assert "lively" in payload["summary"]
