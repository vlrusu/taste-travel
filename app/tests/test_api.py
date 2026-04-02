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

    fetch_profile_response = client.get("/api/v1/me/taste-profile")
    assert fetch_profile_response.status_code == 200
    assert fetch_profile_response.json()["id"] == profile["id"]

    delete_response = client.delete(f"/api/v1/me/seeds/{seed_id}")
    assert delete_response.status_code == 204


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
            "destination_city": "San Sebastian",
            "destination_country": "Spain",
        },
    )

    assert generate_response.status_code == 201
    recommendation = generate_response.json()["recommendation"]
    recommendation_id = recommendation["id"]
    assert recommendation["request_context_json"]["destination_city"] == "San Sebastian"
    assert recommendation["restaurant_json"]["city"] == "San Sebastian"

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
