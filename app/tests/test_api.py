def test_health_check(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ai_seed_extraction_accepts_nested_response_output_text():
    from app.services.ai_seed_extraction import AISeedExtractionService

    payload = {
        "output": [
            {
                "content": [
                    {
                        "type": "output_text",
                        "text": "{\"vibe\":[\"warm\"],\"formality\":\"casual\",\"food_style\":[\"creative\"],\"social_feel\":[\"local_leaning\"],\"use_case\":[\"everyday\"],\"cuisine_style\":[\"regional\"],\"confidence\":0.82,\"reasoning_summary\":\"Warm local place.\"}",
                    }
                ]
            }
        ]
    }

    assert (
        AISeedExtractionService._extract_output_text(payload)
        == "{\"vibe\":[\"warm\"],\"formality\":\"casual\",\"food_style\":[\"creative\"],\"social_feel\":[\"local_leaning\"],\"use_case\":[\"everyday\"],\"cuisine_style\":[\"regional\"],\"confidence\":0.82,\"reasoning_summary\":\"Warm local place.\"}"
    )


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


def test_seed_place_search_returns_google_candidates(client, monkeypatch):
    from app.integrations.google_places import GooglePlacesClient

    def fake_search(self, *, name, city):
        return [
            {
                "name": "Time Out Market Lisboa",
                "city": city,
                "formatted_address": "Av. 24 de Julho 49, 1200-479 Lisboa, Portugal",
                "source": "google_places",
                "source_place_id": "abc123",
                "lat": 38.7071,
                "lon": -9.1457,
                "price_level": "$$",
                "rating": 4.5,
                "user_ratings_total": 1520,
                "raw_types": ["restaurant", "bar"],
                "review_summary_text": "Rated 4.5 from 1520 reviews with a local-leaning profile.",
                "editorial_summary_text": "lively / warm place with strong food identity cues.",
                "menu_summary_text": "bar, strong food identity",
                "raw_seed_note_text": None,
                "raw_place_metadata_json": {"name": "Time Out Market Lisboa", "city": "Lisbon"},
                "raw_review_text": "Rated 4.5 from 1520 reviews with a local-leaning profile.",
                "derived_traits_json": {
                    "vibe": ["lively", "warm"],
                    "formality": ["casual_polished"],
                    "food_style": ["strong_food_identity"],
                    "social_feel": ["local_leaning"],
                    "use_case": ["groups"],
                    "cuisine_style": ["wine_bar"],
                },
                "place_traits_json": {
                    "vibe": ["lively", "warm"],
                    "food_style": ["restaurant", "strong food identity"],
                    "tourist_tolerance": ["local-leaning places"],
                    "price_band": "$$",
                    "likely_formality": "balanced",
                    "formality_score": 0.44,
                    "tourist_profile": "local-leaning",
                },
            }
        ]

    monkeypatch.setattr(GooglePlacesClient, "search_seed_places", fake_search)

    response = client.get("/api/v1/me/seeds/search", params={"name": "Time Out Market", "city": "Lisbon"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "Time Out Market Lisboa",
            "city": "Lisbon",
            "formatted_address": "Av. 24 de Julho 49, 1200-479 Lisboa, Portugal",
            "source": "google_places",
            "source_place_id": "abc123",
            "lat": 38.7071,
            "lon": -9.1457,
            "price_level": "$$",
            "rating": 4.5,
            "user_ratings_total": 1520,
            "raw_types": ["restaurant", "bar"],
            "review_summary_text": "Rated 4.5 from 1520 reviews with a local-leaning profile.",
            "editorial_summary_text": "lively / warm place with strong food identity cues.",
            "menu_summary_text": "bar, strong food identity",
            "raw_seed_note_text": None,
            "raw_place_metadata_json": {"name": "Time Out Market Lisboa", "city": "Lisbon"},
            "raw_review_text": "Rated 4.5 from 1520 reviews with a local-leaning profile.",
            "derived_traits_json": {
                "vibe": ["lively", "warm"],
                "formality": ["casual_polished"],
                "food_style": ["strong_food_identity"],
                "social_feel": ["local_leaning"],
                "use_case": ["groups"],
                "cuisine_style": ["wine_bar"],
            },
            "ai_summary_text": None,
            "place_traits_json": {
                "vibe": ["lively", "warm"],
                "food_style": ["restaurant", "strong food identity"],
                "tourist_tolerance": ["local-leaning places"],
                "price_band": "$$",
                "likely_formality": "balanced",
                "formality_score": 0.44,
                "tourist_profile": "local-leaning",
            },
        }
    ]


def test_verified_seed_restaurant_persists_canonical_place_data(client):
    response = client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Time Out Market Lisboa",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "lively and local",
            "source": "google_places",
            "source_place_id": "abc123",
            "formatted_address": "Av. 24 de Julho 49, 1200-479 Lisboa, Portugal",
            "lat": 38.7071,
            "lon": -9.1457,
            "price_level": "$$",
            "rating": 4.5,
            "user_ratings_total": 1520,
            "raw_types": ["restaurant", "bar"],
            "review_summary_text": "Rated 4.5 from 1520 reviews with a local-leaning profile.",
            "editorial_summary_text": "lively / warm place with strong food identity cues.",
            "menu_summary_text": "bar, strong food identity",
            "raw_seed_note_text": "lively and local",
            "raw_place_metadata_json": {"name": "Time Out Market Lisboa", "city": "Lisbon"},
            "raw_review_text": "Rated 4.5 from 1520 reviews with a local-leaning profile.",
            "derived_traits_json": {
                "vibe": ["lively", "warm"],
                "formality": ["casual_polished"],
                "food_style": ["strong_food_identity"],
                "social_feel": ["local_leaning"],
                "use_case": ["groups"],
                "cuisine_style": ["wine_bar"],
            },
            "place_traits_json": {
                "vibe": ["lively", "warm"],
                "food_style": ["restaurant", "strong food identity"],
                "tourist_tolerance": ["local-leaning places"],
                "price_band": "$$",
                "likely_formality": "balanced",
                "formality_score": 0.44,
                "tourist_profile": "local-leaning",
            },
            "is_verified_place": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["source"] == "google_places"
    assert body["source_place_id"] == "abc123"
    assert body["formatted_address"] == "Av. 24 de Julho 49, 1200-479 Lisboa, Portugal"
    assert body["lat"] == 38.7071
    assert body["lon"] == -9.1457
    assert body["price_level"] == "$$"
    assert body["rating"] == 4.5
    assert body["user_ratings_total"] == 1520
    assert body["raw_types"] == ["restaurant", "bar"]
    assert body["review_summary_text"] == "Rated 4.5 from 1520 reviews with a local-leaning profile."
    assert body["editorial_summary_text"] == "lively / warm place with strong food identity cues."
    assert body["menu_summary_text"] == "bar, strong food identity"
    assert body["raw_seed_note_text"] == "lively and local"
    assert body["raw_place_metadata_json"] == {"name": "Time Out Market Lisboa", "city": "Lisbon"}
    assert body["raw_review_text"] == "Rated 4.5 from 1520 reviews with a local-leaning profile."
    assert "local_leaning" in body["derived_traits_json"]["social_feel"]
    assert "neighborhood_favorite" in body["derived_traits_json"]["social_feel"]
    assert body["enrichment_status"] == "deterministic_only"
    assert body["enriched_at"] is not None
    assert body["place_traits_json"]["vibe"] == ["lively", "warm"]
    assert body["is_verified_place"] is True


def test_manual_seed_restaurant_fallback_stores_unverified_place(client):
    response = client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Neighborhood Bistro",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "warm, grounded",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["source"] is None
    assert body["source_place_id"] is None
    assert body["formatted_address"] is None
    assert body["lat"] is None
    assert body["lon"] is None
    assert body["price_level"] is None
    assert body["rating"] is None
    assert body["user_ratings_total"] is None
    assert body["raw_types"] is None
    assert body["review_summary_text"] is None
    assert body["editorial_summary_text"] is None
    assert body["menu_summary_text"] is None
    assert body["raw_seed_note_text"] == "warm, grounded"
    assert body["raw_place_metadata_json"] is None
    assert body["raw_review_text"] is None
    assert body["derived_traits_json"] is None
    assert body["enrichment_status"] == "manual"
    assert body["enriched_at"] is None
    assert body["place_traits_json"] is None
    assert body["is_verified_place"] is False


def test_taste_profile_uses_verified_place_traits_when_notes_are_missing(client, monkeypatch):
    from app.services.ai_seed_extraction import AISeedExtractionService

    def fake_extract(self, **kwargs):
        return {
            "vibe": ["warm", "local", "unpretentious"],
            "formality": "casual",
            "food_style": ["strong_food_identity"],
            "social_feel": ["local_leaning", "neighborhood_favorite"],
            "use_case": ["everyday"],
            "cuisine_style": ["seafood", "small_plates"],
            "confidence": 0.82,
            "reasoning_summary": "Warm local seafood place with strong food identity.",
        }

    monkeypatch.setattr(AISeedExtractionService, "extract_traits", fake_extract)

    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Time Out Market Lisboa",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": None,
            "source": "google_places",
            "source_place_id": "abc123",
            "formatted_address": "Av. 24 de Julho 49, 1200-479 Lisboa, Portugal",
            "lat": 38.7071,
            "lon": -9.1457,
            "price_level": "$$",
            "rating": 4.5,
            "user_ratings_total": 1520,
            "raw_types": ["restaurant", "bar"],
            "review_summary_text": "Crowded, lively, and deeply local with strong seafood identity.",
            "editorial_summary_text": "Warm neighborhood room with buzzy energy.",
            "menu_summary_text": "seafood, small plates, regional wine",
            "place_traits_json": {
                "vibe": ["lively", "warm", "grounded"],
                "food_style": ["strong food identity", "restaurant"],
                "tourist_tolerance": ["prefers local-leaning places"],
                "price_band": "$$",
                "likely_formality": "balanced",
                "formality_score": 0.44,
                "tourist_profile": "local-leaning",
            },
            "is_verified_place": True,
        },
    )

    response = client.post("/api/v1/me/taste-profile:generate")

    assert response.status_code == 200
    attributes = response.json()["taste_profile"]["attributes_json"]
    assert "lively" in attributes["vibe"]
    assert "warm" in attributes["vibe"]
    assert "unpretentious" in attributes["vibe"]
    assert "strong food identity" in attributes["food_style"]
    assert "prefers local-leaning places" in attributes["tourist_tolerance"]
    assert attributes["verified_place_restaurants"] == ["Time Out Market Lisboa"]


def test_text_enrichment_generates_normalized_traits(client):
    response = client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Late Glass",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": None,
            "source": "google_places",
            "source_place_id": "seed-2",
            "formatted_address": "Rua Example 10, Lisbon",
            "lat": 38.71,
            "lon": -9.14,
            "price_level": "$$$",
            "rating": 4.6,
            "user_ratings_total": 220,
            "raw_types": ["restaurant", "bar"],
            "review_summary_text": "Buzzy, stylish room that feels lively and great for groups.",
            "editorial_summary_text": "A polished date night spot with strong chef-driven energy.",
            "menu_summary_text": "Small plates, seafood, and regional wine.",
            "is_verified_place": True,
        },
    )

    assert response.status_code == 201
    traits = response.json()["derived_traits_json"]
    assert "buzzy" in traits["vibe"]
    assert "stylish" in traits["vibe"]
    assert "groups" in traits["use_case"]
    assert "date_night" in traits["use_case"]
    assert "chef_driven" in traits["food_style"]
    assert "small_plates" in traits["cuisine_style"]
    assert "seafood" in traits["cuisine_style"]


def test_ai_derived_traits_are_stored_in_stable_json_format(client, monkeypatch):
    from app.services.ai_seed_extraction import AISeedExtractionService

    def fake_extract(self, **kwargs):
        return {
            "vibe": ["stylish", "romantic"],
            "formality": "casual_polished",
            "food_style": ["chef_driven", "creative"],
            "social_feel": ["destination"],
            "use_case": ["date_night", "special_occasion"],
            "cuisine_style": ["small_plates", "wine_bar"],
            "confidence": 0.78,
            "reasoning_summary": "Stylish chef-driven place suited to date nights.",
        }

    monkeypatch.setattr(AISeedExtractionService, "extract_traits", fake_extract)

    response = client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Atelier Glass",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": None,
            "source": "google_places",
            "source_place_id": "ai-1",
            "formatted_address": "Rua Atelier 4, Lisbon",
            "lat": 38.71,
            "lon": -9.14,
            "price_level": "$$$",
            "rating": 4.6,
            "user_ratings_total": 180,
            "raw_types": ["restaurant", "bar"],
            "review_summary_text": "Stylish and energetic.",
            "editorial_summary_text": "Chef-driven room with date-night energy.",
            "menu_summary_text": "small plates and wine",
            "is_verified_place": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["derived_traits_json"]["vibe"] == ["lively", "warm", "buzzy", "energetic", "stylish", "romantic"]
    assert body["derived_traits_json"]["formality"] == ["casual_polished"]
    assert body["derived_traits_json"]["food_style"] == ["strong_food_identity", "chef_driven", "creative"]
    assert body["derived_traits_json"]["social_feel"] == ["local_leaning", "neighborhood_favorite", "destination"]
    assert body["derived_traits_json"]["use_case"] == ["groups", "late_night", "date_night", "special_occasion"]
    assert body["derived_traits_json"]["cuisine_style"] == ["wine_bar", "small_plates"]
    assert body["derived_traits_json"]["primary_archetype"] in {"chef_driven_small_plates", "neighborhood_wine_bar"}
    assert "food_forward" in body["derived_traits_json"]["positive_traits"]
    assert body["ai_summary_text"] == "Stylish chef-driven place suited to date nights."
    assert body["enrichment_status"] == "ai_completed"


def test_verified_seed_with_precomputed_traits_still_uses_ai_when_available(client, monkeypatch):
    from app.services.ai_seed_extraction import AISeedExtractionService

    def fake_extract(self, **kwargs):
        return {
            "vibe": ["unpretentious", "grounded"],
            "formality": "casual",
            "food_style": ["creative"],
            "social_feel": ["local_leaning"],
            "use_case": ["everyday"],
            "cuisine_style": ["regional"],
            "confidence": 0.71,
            "reasoning_summary": "Grounded local place with a creative edge.",
        }

    monkeypatch.setattr(AISeedExtractionService, "extract_traits", fake_extract)

    response = client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Market Table",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": None,
            "source": "google_places",
            "source_place_id": "precomputed-1",
            "formatted_address": "Rua Mercado 3, Lisbon",
            "lat": 38.71,
            "lon": -9.14,
            "price_level": "$$",
            "rating": 4.5,
            "user_ratings_total": 140,
            "raw_types": ["restaurant"],
            "review_summary_text": "Warm local dining room.",
            "editorial_summary_text": "Neighborhood spot with strong food identity.",
            "menu_summary_text": "regional seafood",
            "derived_traits_json": {
                "vibe": ["warm"],
                "formality": ["casual_polished"],
                "food_style": ["strong_food_identity"],
                "social_feel": ["neighborhood_favorite"],
                "use_case": ["groups"],
                "cuisine_style": ["seafood"],
            },
            "is_verified_place": True,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["enrichment_status"] == "ai_completed"
    assert body["ai_summary_text"] == "Grounded local place with a creative edge."
    assert "warm" in body["derived_traits_json"]["vibe"]
    assert "grounded" in body["derived_traits_json"]["vibe"]
    assert "creative" in body["derived_traits_json"]["food_style"]
    assert "regional" in body["derived_traits_json"]["cuisine_style"]


def test_verified_seed_improves_profile_over_manual_seed(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Manual Spot",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": None,
        },
    )
    manual_profile = client.post("/api/v1/me/taste-profile:generate").json()["taste_profile"]

    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Verified Spot",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": None,
            "source": "google_places",
            "source_place_id": "verified-1",
            "formatted_address": "Rua Verified 12, Lisbon",
            "lat": 38.72,
            "lon": -9.13,
            "price_level": "$$",
            "rating": 4.7,
            "user_ratings_total": 340,
            "raw_types": ["restaurant", "bar"],
            "review_summary_text": "Warm, grounded, lively neighborhood place.",
            "editorial_summary_text": "Local favorite with strong food identity.",
            "menu_summary_text": "Regional seafood and small plates.",
            "is_verified_place": True,
        },
    )
    improved_profile = client.post("/api/v1/me/taste-profile:generate").json()["taste_profile"]

    assert len(improved_profile["attributes_json"]["vibe"]) > len(manual_profile["attributes_json"]["vibe"])
    assert improved_profile["attributes_json"]["verified_place_restaurants"] == ["Verified Spot"]


def test_recommendation_ranking_changes_when_ai_enriched_traits_are_present(client, monkeypatch):
    from app.services.ai_seed_extraction import AISeedExtractionService

    def fake_extract(self, **kwargs):
        return {
            "vibe": ["warm", "grounded", "local"],
            "formality": "casual",
            "food_style": ["strong_food_identity"],
            "social_feel": ["local_leaning", "neighborhood_favorite"],
            "use_case": ["everyday"],
            "cuisine_style": ["regional", "small_plates"],
            "confidence": 0.88,
            "reasoning_summary": "Local grounded place with strong regional food identity.",
        }

    monkeypatch.setattr(AISeedExtractionService, "extract_traits", fake_extract)

    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Verified Spot",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": None,
            "source": "google_places",
            "source_place_id": "verified-rank",
            "formatted_address": "Rua Verified 12, Lisbon",
            "lat": 38.72,
            "lon": -9.13,
            "price_level": "$$",
            "rating": 4.7,
            "user_ratings_total": 340,
            "raw_types": ["restaurant", "bar"],
            "review_summary_text": "Warm, grounded, lively neighborhood place.",
            "editorial_summary_text": "Local favorite with strong food identity.",
            "menu_summary_text": "Regional seafood and small plates.",
            "is_verified_place": True,
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
                "special_request": "local and not too formal",
            },
        },
    )

    assert response.status_code == 201
    top = response.json()["recommendations"][0]
    assert top["anchors_json"]["score_breakdown"]["vibe_match_score"] > 0.3


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


def test_recent_feedback_feeds_back_into_recommendation_scoring(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Local Bistro",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "warm, neighborhood feel, strong food",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    first_response = client.post(
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

    assert first_response.status_code == 201
    initial_recommendations = first_response.json()["recommendations"]
    by_name = {item["restaurant_json"]["name"]: item for item in initial_recommendations}

    pricey_recommendation = initial_recommendations[-1]
    positive_recommendation = next(
        item
        for item in initial_recommendations
        if item["restaurant_json"]["tourist_profile"] == "local-leaning"
        and "strong food identity" in item["restaurant_json"]["cuisine_tags"]
    )

    too_formal_response = client.post(
        f"/api/v1/recommendations/{pricey_recommendation['id']}/feedback",
        json={"feedback_type": "too_formal"},
    )
    assert too_formal_response.status_code == 200

    good_fit_response = client.post(
        f"/api/v1/recommendations/{positive_recommendation['id']}/feedback",
        json={"feedback_type": "perfect"},
    )
    assert good_fit_response.status_code == 200

    second_response = client.post(
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

    assert second_response.status_code == 201
    next_recommendations = second_response.json()["recommendations"]
    next_by_name = {item["restaurant_json"]["name"]: item for item in next_recommendations}

    assert pricey_recommendation["restaurant_json"]["name"] not in next_by_name
    assert next_by_name[positive_recommendation["restaurant_json"]["name"]]["anchors_json"]["score_breakdown"]["feedback_adjustment_score"] > 0
    assert next_recommendations[0]["restaurant_json"]["tourist_profile"] == "local-leaning"


def test_recent_negative_feedback_excludes_same_restaurant_from_next_results(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Local Bistro",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "warm, neighborhood feel, strong food",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    first_response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Lisbon", "lat": 38.7223, "lon": -9.1393},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "local feel",
            },
        },
    )

    assert first_response.status_code == 201
    destination_pick = first_response.json()["recommendations"][-1]

    feedback_response = client.post(
        f"/api/v1/recommendations/{destination_pick['id']}/feedback",
        json={"feedback_type": "too_touristy"},
    )
    assert feedback_response.status_code == 200

    second_response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Lisbon", "lat": 38.7223, "lon": -9.1393},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "local feel",
            },
        },
    )

    assert second_response.status_code == 201
    next_names = [item["restaurant_json"]["name"] for item in second_response.json()["recommendations"]]
    assert destination_pick["restaurant_json"]["name"] not in next_names


def test_rejecting_entire_first_batch_does_not_return_same_list(client):
    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Local Bistro",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "warm, neighborhood feel, strong food",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    first_response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Lisbon", "lat": 38.7223, "lon": -9.1393},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "local feel",
            },
        },
    )

    assert first_response.status_code == 201
    first_recommendations = first_response.json()["recommendations"]
    first_names = [item["restaurant_json"]["name"] for item in first_recommendations]
    assert len(first_names) == 5

    for item in first_recommendations:
        feedback_response = client.post(
            f"/api/v1/recommendations/{item['id']}/feedback",
            json={"feedback_type": "dismissed"},
        )
        assert feedback_response.status_code == 200

    second_response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Lisbon", "lat": 38.7223, "lon": -9.1393},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "local feel",
            },
        },
    )

    assert second_response.status_code == 201
    second_names = [item["restaurant_json"]["name"] for item in second_response.json()["recommendations"]]
    assert second_names
    assert set(first_names).isdisjoint(second_names)


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
    cheap_or_match_positions = [
        index
        for index, item in enumerate(recommendations)
        if item["restaurant_json"]["price_level"] in {"$", "$$"}
    ]
    assert cheap_or_match_positions
    assert all(item["restaurant_json"]["price_level"] in {"$", "$$"} for item in recommendations[:3])


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
    assert all(item["restaurant_json"]["formality_score"] < 0.6 for item in recommendations[:3])
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

    def fake_search(self, *, city, country, lat, lon, radius_meters, meal_type=None):
        seen["search_city"] = city
        seen["lat"] = lat
        seen["lon"] = lon
        seen["radius_meters"] = radius_meters
        seen["meal_type"] = meal_type
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
        "meal_type": "dinner",
    }


def test_recommendations_expand_google_search_after_suppression_before_using_fallback(client, monkeypatch):
    from app.integrations.google_places import GooglePlacesClient

    def candidate(name: str, place_id: str) -> dict:
        return {
            "restaurant_json": {
                "name": name,
                "city": "Lisbon",
                "country": "Portugal",
                "source": "google_places",
                "google_place_id": place_id,
                "price_level": "$$",
                "cuisine_tags": ["regional", "strong food identity"],
                "vibe_tags": ["warm", "grounded", "local-favorite"],
                "formality_score": 0.24,
                "tourist_profile": "local-leaning",
            }
        }

    seen_radii: list[int] = []

    def fake_search(self, *, city, country, lat, lon, radius_meters, meal_type=None):
        seen_radii.append(radius_meters)
        if radius_meters == 2000:
            return [candidate(f"Lisbon Base {index}", f"base-{index}") for index in range(1, 6)]
        if radius_meters == 4000:
            return [candidate(f"Lisbon Wider {index}", f"wide-{index}") for index in range(1, 6)]
        return []

    monkeypatch.setattr(GooglePlacesClient, "search_restaurants", fake_search)

    client.post(
        "/api/v1/me/seeds",
        json={
            "name": "Local Bistro",
            "city": "Lisbon",
            "sentiment": "love",
            "notes": "warm, neighborhood feel, strong food",
        },
    )
    client.post("/api/v1/me/taste-profile:generate")

    first_response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Lisbon", "lat": 38.7223, "lon": -9.1393},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "local feel",
            },
        },
    )

    assert first_response.status_code == 201
    first_recommendations = first_response.json()["recommendations"]
    assert all(item["restaurant_json"]["source"] == "google_places" for item in first_recommendations)

    for item in first_recommendations:
        feedback_response = client.post(
            f"/api/v1/recommendations/{item['id']}/feedback",
            json={"feedback_type": "dismissed"},
        )
        assert feedback_response.status_code == 200

    second_response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Lisbon", "lat": 38.7223, "lon": -9.1393},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "local feel",
            },
        },
    )

    assert second_response.status_code == 201
    second_recommendations = second_response.json()["recommendations"]
    assert all(item["restaurant_json"]["source"] == "google_places" for item in second_recommendations)
    assert all(item["restaurant_json"]["name"].startswith("Lisbon Wider") for item in second_recommendations)
    assert 4000 in seen_radii


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


def test_rootstock_avec_style_seeds_infer_corporate_and_generic_upscale_anti_signals(client):
    for name, archetype, positives in [
        (
            "Rootstock",
            "neighborhood_wine_bar",
            ["local_leaning", "independent", "characterful", "food_forward", "strong_food_identity", "unpretentious"],
        ),
        (
            "Avec",
            "chef_driven_small_plates",
            ["local_leaning", "chef_driven", "characterful", "food_forward", "strong_food_identity", "culturally_specific"],
        ),
    ]:
        response = client.post(
            "/api/v1/me/seeds",
            json={
                "name": name,
                "city": "Chicago",
                "sentiment": "love",
                "notes": None,
                "source": "google_places",
                "source_place_id": f"{name.lower()}-1",
                "formatted_address": f"{name} address",
                "lat": 41.0,
                "lon": -87.0,
                "price_level": "$$",
                "rating": 4.6,
                "user_ratings_total": 240,
                "raw_types": ["restaurant", "bar"],
                "review_summary_text": "Neighborhood energy with strong food identity.",
                "editorial_summary_text": "Characterful room with a clear point of view.",
                "menu_summary_text": "small plates, wine, regional cooking",
                "derived_traits_json": {
                    "vibe": ["warm", "grounded", "local"],
                    "formality": ["casual_polished"],
                    "food_style": ["strong_food_identity", "chef_driven"],
                    "social_feel": ["local_leaning", "neighborhood_favorite"],
                    "use_case": ["date_night", "everyday"],
                    "cuisine_style": ["small_plates", "wine_bar", "regional"],
                    "primary_archetype": archetype,
                    "secondary_archetypes": ["design_forward_casual"],
                    "positive_traits": positives,
                    "negative_traits": [],
                    "confidence_score": 0.9,
                },
                "place_traits_json": {
                    "vibe": ["warm", "grounded", "local-favorite"],
                    "food_style": ["strong food identity"],
                    "tourist_tolerance": ["prefers local-leaning places"],
                    "price_band": "$$",
                    "likely_formality": "balanced",
                    "formality_score": 0.34,
                    "tourist_profile": "local-leaning",
                    "primary_archetype": archetype,
                    "positive_traits": positives,
                    "negative_traits": [],
                },
                "is_verified_place": True,
            },
        )
        assert response.status_code == 201

    profile = client.post("/api/v1/me/taste-profile:generate").json()["taste_profile"]
    anti_signals = set(profile["attributes_json"]["inferred_anti_signals"])
    liked_archetypes = set(profile["attributes_json"]["liked_archetypes"])

    assert "corporate" in anti_signals
    assert "generic upscale" in anti_signals
    assert "business district" in anti_signals
    assert "neighborhood wine bar" in liked_archetypes
    assert "chef driven small plates" in liked_archetypes


def test_rootstock_avec_profile_ranks_local_food_forward_above_corporate_upscale(client, monkeypatch):
    from app.integrations.google_places import GooglePlacesClient

    for name, archetype in [
        ("Rootstock", "neighborhood_wine_bar"),
        ("Avec", "chef_driven_small_plates"),
    ]:
        client.post(
            "/api/v1/me/seeds",
            json={
                "name": name,
                "city": "Chicago",
                "sentiment": "love",
                "notes": None,
                "source": "google_places",
                "source_place_id": f"{name.lower()}-2",
                "formatted_address": f"{name} address",
                "lat": 41.0,
                "lon": -87.0,
                "price_level": "$$",
                "rating": 4.6,
                "user_ratings_total": 240,
                "raw_types": ["restaurant", "bar"],
                "review_summary_text": "Neighborhood energy with strong food identity.",
                "editorial_summary_text": "Characterful room with a clear point of view.",
                "menu_summary_text": "small plates, wine, regional cooking",
                "derived_traits_json": {
                    "vibe": ["warm", "grounded", "local"],
                    "formality": ["casual_polished"],
                    "food_style": ["strong_food_identity", "chef_driven"],
                    "social_feel": ["local_leaning", "neighborhood_favorite"],
                    "use_case": ["date_night", "everyday"],
                    "cuisine_style": ["small_plates", "wine_bar", "regional"],
                    "primary_archetype": archetype,
                    "secondary_archetypes": ["design_forward_casual"],
                    "positive_traits": ["local_leaning", "independent", "characterful", "food_forward", "strong_food_identity"],
                    "negative_traits": [],
                    "confidence_score": 0.9,
                },
                "place_traits_json": {
                    "tourist_tolerance": ["prefers local-leaning places"],
                    "price_band": "$$",
                    "likely_formality": "balanced",
                    "formality_score": 0.34,
                    "tourist_profile": "local-leaning",
                    "primary_archetype": archetype,
                    "positive_traits": ["local_leaning", "independent", "characterful", "food_forward", "strong_food_identity"],
                    "negative_traits": [],
                },
                "is_verified_place": True,
            },
        )

    client.post("/api/v1/me/taste-profile:generate")

    def fake_search(self, *, city, country, lat, lon, radius_meters, meal_type=None):
        return [
            {
                "restaurant_json": {
                    "name": "Ocean Prime Chicago",
                    "city": city,
                    "country": "USA",
                    "source": "google_places",
                    "price_level": "$$$$",
                    "raw_types": ["restaurant", "seafood_restaurant", "steak_house"],
                    "cuisine_tags": ["seafood", "restaurant", "strong food identity"],
                    "vibe_tags": ["refined", "stylish", "upscale"],
                    "formality_score": 0.91,
                    "tourist_profile": "destination",
                    "address": "Downtown business district hotel lobby",
                }
            },
            {
                "restaurant_json": {
                    "name": "Cellar Door Chicago",
                    "city": city,
                    "country": "USA",
                    "source": "google_places",
                    "price_level": "$$",
                    "raw_types": ["restaurant", "bar"],
                    "cuisine_tags": ["small_plates", "wine_bar", "regional", "strong food identity"],
                    "vibe_tags": ["warm", "grounded", "local-favorite", "shared-plates", "neighborhood"],
                    "formality_score": 0.28,
                    "tourist_profile": "local-leaning",
                    "address": "Neighborhood corner dining room",
                }
            },
            {
                "restaurant_json": {
                    "name": "Market Stove Chicago",
                    "city": city,
                    "country": "USA",
                    "source": "google_places",
                    "price_level": "$$",
                    "raw_types": ["restaurant"],
                    "cuisine_tags": ["regional", "bistro", "strong food identity"],
                    "vibe_tags": ["warm", "grounded", "authentic"],
                    "formality_score": 0.32,
                    "tourist_profile": "local-leaning",
                    "address": "Local main street bistro",
                }
            },
        ]

    monkeypatch.setattr(GooglePlacesClient, "search_restaurants", fake_search)

    response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Chicago", "lat": 41.8781, "lon": -87.6298},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "food-first, local, not too formal",
            },
        },
    )

    assert response.status_code == 201
    recommendations = response.json()["recommendations"]
    names = [item["restaurant_json"]["name"] for item in recommendations]
    assert names[0] in {"Cellar Door Chicago", "Market Stove Chicago"}
    assert names[-1] == "Ocean Prime Chicago"
    ocean_prime = next(item for item in recommendations if item["restaurant_json"]["name"] == "Ocean Prime Chicago")
    assert ocean_prime["anchors_json"]["score_breakdown"]["corporate_penalty"] > 0
    assert ocean_prime["anchors_json"]["score_breakdown"]["generic_upscale_penalty"] > 0
    assert "corporate" in ocean_prime["why"] or "generic-upscale" in ocean_prime["why"]


def test_corporate_upscale_seed_profile_can_prefer_polished_destination_dining(client, monkeypatch):
    from app.integrations.google_places import GooglePlacesClient

    for name, archetype, positives, negatives in [
        (
            "Ocean Prime",
            "corporate_seafood_steak",
            ["polished_luxury", "safe_luxury", "business_district", "luxury_consistency"],
            ["corporate", "generic_upscale", "business_district"],
        ),
        (
            "Maple & Ash",
            "business_district_dining",
            ["polished_luxury", "safe_luxury", "business_district"],
            ["generic_upscale", "business_district"],
        ),
    ]:
        client.post(
            "/api/v1/me/seeds",
            json={
                "name": name,
                "city": "Chicago",
                "sentiment": "love",
                "notes": "polished, upscale, special occasion dinner",
                "source": "google_places",
                "source_place_id": f"{name.lower().replace(' ', '-')}-pref",
                "formatted_address": f"{name} downtown",
                "lat": 41.0,
                "lon": -87.0,
                "price_level": "$$$$",
                "rating": 4.5,
                "user_ratings_total": 520,
                "raw_types": ["restaurant", "seafood_restaurant", "steak_house"],
                "review_summary_text": "Polished business-district dining room with strong service.",
                "editorial_summary_text": "Upscale destination dinner with a luxury feel.",
                "menu_summary_text": "seafood, steak, classic cocktails",
                "derived_traits_json": {
                    "vibe": ["stylish"],
                    "formality": ["formal"],
                    "food_style": ["strong_food_identity", "classic"],
                    "social_feel": ["destination"],
                    "use_case": ["special_occasion", "date_night"],
                    "cuisine_style": ["seafood"],
                    "primary_archetype": archetype,
                    "secondary_archetypes": ["tourist_favorite"],
                    "positive_traits": positives,
                    "negative_traits": negatives,
                    "confidence_score": 0.88,
                },
                "place_traits_json": {
                    "tourist_tolerance": ["open but selective"],
                    "price_band": "$$$$",
                    "likely_formality": "formal",
                    "formality_score": 0.9,
                    "tourist_profile": "destination",
                    "primary_archetype": archetype,
                    "positive_traits": positives,
                    "negative_traits": negatives,
                },
                "is_verified_place": True,
            },
        )

    profile = client.post("/api/v1/me/taste-profile:generate").json()["taste_profile"]
    assert "corporate" not in set(profile["attributes_json"]["negative_traits"])

    def fake_search(self, *, city, country, lat, lon, radius_meters, meal_type=None):
        return [
            {
                "restaurant_json": {
                    "name": "Ocean Prime Chicago",
                    "city": city,
                    "country": "USA",
                    "source": "google_places",
                    "price_level": "$$$$",
                    "raw_types": ["restaurant", "seafood_restaurant", "steak_house"],
                    "cuisine_tags": ["seafood", "restaurant", "strong food identity"],
                    "vibe_tags": ["refined", "stylish", "upscale"],
                    "formality_score": 0.91,
                    "tourist_profile": "destination",
                    "address": "Downtown business district hotel lobby",
                }
            },
            {
                "restaurant_json": {
                    "name": "Cellar Door Chicago",
                    "city": city,
                    "country": "USA",
                    "source": "google_places",
                    "price_level": "$$",
                    "raw_types": ["restaurant", "bar"],
                    "cuisine_tags": ["small_plates", "wine_bar", "regional", "strong food identity"],
                    "vibe_tags": ["warm", "grounded", "local-favorite", "shared-plates", "neighborhood"],
                    "formality_score": 0.28,
                    "tourist_profile": "local-leaning",
                    "address": "Neighborhood corner dining room",
                }
            },
        ]

    monkeypatch.setattr(GooglePlacesClient, "search_restaurants", fake_search)

    response = client.post(
        "/api/v1/recommendations:generate",
        json={
            "location": {"city": "Chicago", "lat": 41.8781, "lon": -87.6298},
            "context": {
                "meal_type": "dinner",
                "party_size": 2,
                "budget": "$$$$",
                "max_distance_meters": 2000,
                "transport_mode": "walk",
                "special_request": "special occasion dinner",
            },
        },
    )

    assert response.status_code == 201
    recommendations = response.json()["recommendations"]
    ocean_prime = next(item for item in recommendations if item["restaurant_json"]["name"] == "Ocean Prime Chicago")
    assert ocean_prime["anchors_json"]["score_breakdown"]["corporate_penalty"] == 0
    assert ocean_prime["anchors_json"]["score_breakdown"]["generic_upscale_penalty"] == 0
    assert ocean_prime["anchors_json"]["score_breakdown"]["upscale_affinity_score"] > 0
