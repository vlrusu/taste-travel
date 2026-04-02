"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  Recommendation,
  RecommendationFeedbackType,
  SeedRestaurant,
  TasteProfile,
  User,
  createSeed,
  deleteSeed,
  generateRecommendations,
  generateTasteProfile,
  getMe,
  getSeeds,
  submitRecommendationFeedback,
  updateMe,
} from "../lib/api";

import styles from "./page.module.css";

const initialSeedForm = {
  name: "",
  city: "",
  sentiment: "love" as "love" | "dislike",
  notes: "",
};

const initialRecommendationForm = {
  city: "",
  meal_type: "dinner",
  party_size: "2",
  budget: "$$",
  max_distance_meters: "2000",
  transport_mode: "walk",
  special_request: "memorable but not too formal",
};

const feedbackOptions: Array<{
  label: string;
  value: RecommendationFeedbackType;
}> = [
  { label: "Good fit", value: "perfect" },
  { label: "Not my vibe", value: "not_my_vibe" },
  { label: "Too formal", value: "too_formal" },
  { label: "Too touristy", value: "too_touristy" },
  { label: "Too expensive", value: "too_expensive" },
];

function buildGoogleMapsUrl(recommendation: Recommendation): string {
  const restaurant = recommendation.restaurant_json;
  const placeId = typeof restaurant.google_place_id === "string" ? restaurant.google_place_id : null;
  if (placeId) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
      restaurant.name,
    )}&query_place_id=${encodeURIComponent(placeId)}`;
  }

  const queryParts = [
    restaurant.name,
    typeof restaurant.address === "string" ? restaurant.address : null,
    restaurant.city,
    typeof restaurant.country === "string" ? restaurant.country : null,
  ].filter(Boolean);

  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(queryParts.join(", "))}`;
}

function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackError, setFeedbackError] = useState<string | null>(null);
  const [feedbackSaved, setFeedbackSaved] = useState(false);
  const mapsUrl = buildGoogleMapsUrl(recommendation);

  async function handleFeedback(feedbackType: RecommendationFeedbackType) {
    try {
      setFeedbackLoading(true);
      setFeedbackError(null);
      setFeedbackSaved(false);
      await submitRecommendationFeedback(recommendation.id, feedbackType);
      setFeedbackSaved(true);
    } catch (error) {
      setFeedbackError(error instanceof Error ? error.message : "Failed to save feedback");
      setFeedbackSaved(false);
    } finally {
      setFeedbackLoading(false);
    }
  }

  return (
    <div className={styles.recommendationCard}>
      <div className={styles.cardTop}>
        <div>
          <h3 className={styles.restaurantName}>
            <a href={mapsUrl} target="_blank" rel="noreferrer" className={styles.restaurantLink}>
              {recommendation.restaurant_json.name}
            </a>
          </h3>
          <p className={styles.locationLine}>
            {recommendation.restaurant_json.city}
            {recommendation.restaurant_json.country ? `, ${recommendation.restaurant_json.country}` : ""}
          </p>
        </div>
        <div className={styles.metaGroup}>
          <span className={styles.pricePill}>{recommendation.restaurant_json.price_level}</span>
          <span className={styles.score}>Score {recommendation.score.toFixed(2)}</span>
        </div>
      </div>

      <div className={styles.detailGroup}>
        <div>
          <p className={styles.detailLabel}>Cuisine tags</p>
          <div className={styles.tagList}>
            {recommendation.restaurant_json.cuisine_tags.map((tag) => (
              <span key={`${recommendation.id}-${tag}`} className={styles.tag}>
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div>
          <p className={styles.detailLabel}>Vibe tags</p>
          <div className={styles.tagList}>
            {recommendation.restaurant_json.vibe_tags.map((tag) => (
              <span key={`${recommendation.id}-vibe-${tag}`} className={styles.tag}>
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className={styles.whyBlock}>
        <p className={styles.detailLabel}>Why it fits</p>
        <p>{recommendation.why}</p>
      </div>

      <div className={styles.traitGrid}>
        <div className={styles.traitSection}>
          <p className={styles.detailLabel}>Matched traits</p>
          {recommendation.anchors_json.matched_traits?.length ? (
            <ul className={styles.traitList}>
              {recommendation.anchors_json.matched_traits.map((trait) => (
                <li key={`${recommendation.id}-match-${trait}`}>{trait}</li>
              ))}
            </ul>
          ) : (
            <p className={styles.subtle}>No strong positive traits highlighted.</p>
          )}
        </div>

        <div className={styles.traitSection}>
          <p className={styles.detailLabel}>Caution traits</p>
          {recommendation.anchors_json.caution_traits?.length ? (
            <ul className={styles.traitList}>
              {recommendation.anchors_json.caution_traits.map((trait) => (
                <li key={`${recommendation.id}-caution-${trait}`}>{trait}</li>
              ))}
            </ul>
          ) : (
            <p className={styles.subtle}>No caution traits for this result.</p>
          )}
        </div>
      </div>

      <div className={styles.feedbackBlock}>
        <p className={styles.detailLabel}>Quick feedback</p>
        <div className={styles.feedbackActions}>
          {feedbackOptions.map((option) => (
            <button
              key={`${recommendation.id}-${option.value}`}
              type="button"
              className={styles.feedbackButton}
              onClick={() => void handleFeedback(option.value)}
              disabled={feedbackLoading}
            >
              {feedbackLoading ? "Saving…" : option.label}
            </button>
          ))}
        </div>
        {feedbackSaved ? <p className={styles.feedbackSaved}>Feedback saved</p> : null}
        {feedbackError ? <p className={styles.error}>{feedbackError}</p> : null}
      </div>
    </div>
  );
}

export default function Page() {
  const [user, setUser] = useState<User | null>(null);
  const [homeCity, setHomeCity] = useState("");
  const [profileLoading, setProfileLoading] = useState(true);
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileError, setProfileError] = useState<string | null>(null);

  const [seeds, setSeeds] = useState<SeedRestaurant[]>([]);
  const [seedForm, setSeedForm] = useState(initialSeedForm);
  const [seedsLoading, setSeedsLoading] = useState(true);
  const [seedSubmitting, setSeedSubmitting] = useState(false);
  const [deletingSeedId, setDeletingSeedId] = useState<string | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);

  const [tasteProfile, setTasteProfile] = useState<TasteProfile | null>(null);
  const [tasteLoading, setTasteLoading] = useState(false);
  const [tasteError, setTasteError] = useState<string | null>(null);

  const [recommendationForm, setRecommendationForm] = useState(initialRecommendationForm);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);

  async function refreshSeeds() {
    setSeedsLoading(true);
    try {
      const updatedSeeds = await getSeeds();
      setSeeds(updatedSeeds);
    } catch (error) {
      throw error instanceof Error ? error : new Error("Failed to load seed restaurants");
    } finally {
      setSeedsLoading(false);
    }
  }

  useEffect(() => {
    async function loadInitialData() {
      try {
        setProfileLoading(true);
        const [me, seedList] = await Promise.all([getMe(), getSeeds()]);
        setUser(me);
        setHomeCity(me.home_city ?? "");
        setSeeds(seedList);
      } catch (error) {
        const message = error instanceof Error ? error.message : "Failed to load data";
        setProfileError(message);
        setSeedError(message);
      } finally {
        setProfileLoading(false);
        setSeedsLoading(false);
      }
    }

    void loadInitialData();
  }, []);

  async function handleProfileSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setProfileSaving(true);
      setProfileError(null);
      const updated = await updateMe({ home_city: homeCity.trim() || null });
      setUser(updated);
      setHomeCity(updated.home_city ?? "");
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Failed to save profile");
    } finally {
      setProfileSaving(false);
    }
  }

  async function handleSeedSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setSeedSubmitting(true);
      setSeedError(null);
      await createSeed({
        ...seedForm,
        notes: seedForm.notes.trim(),
      });
      await refreshSeeds();
      setSeedForm(initialSeedForm);
    } catch (error) {
      setSeedError(error instanceof Error ? error.message : "Failed to create seed restaurant");
    } finally {
      setSeedSubmitting(false);
    }
  }

  async function handleGenerateTasteProfile() {
    try {
      setTasteLoading(true);
      setTasteError(null);
      const response = await generateTasteProfile();
      setTasteProfile(response.taste_profile);
    } catch (error) {
      setTasteError(error instanceof Error ? error.message : "Failed to generate taste profile");
    } finally {
      setTasteLoading(false);
    }
  }

  async function handleDeleteSeed(seedId: string) {
    try {
      setDeletingSeedId(seedId);
      setSeedError(null);
      await deleteSeed(seedId);
      await refreshSeeds();
    } catch (error) {
      setSeedError(error instanceof Error ? error.message : "Failed to delete seed restaurant");
    } finally {
      setDeletingSeedId(null);
    }
  }

  async function handleRecommendationSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setRecommendationLoading(true);
      setRecommendationError(null);
      const response = await generateRecommendations({
        location: {
          city: recommendationForm.city.trim(),
        },
        context: {
          meal_type: recommendationForm.meal_type,
          party_size: Number(recommendationForm.party_size),
          budget: recommendationForm.budget,
          max_distance_meters: Number(recommendationForm.max_distance_meters),
          transport_mode: recommendationForm.transport_mode,
          special_request: recommendationForm.special_request,
        },
      });
      setRecommendations(response.recommendations);
    } catch (error) {
      setRecommendationError(error instanceof Error ? error.message : "Failed to generate recommendations");
    } finally {
      setRecommendationLoading(false);
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.hero}>
        <div>
          <p className={styles.eyebrow}>Taste Travel MVP</p>
          <h1>Restaurant recommendations shaped by your travel taste profile.</h1>
          <p className={styles.subtle}>
            Single-page Next.js client for the local FastAPI backend running at
            {" "}
            <code>http://127.0.0.1:8000/api/v1</code>.
          </p>
        </div>
      </section>

      <section className={styles.grid}>
        <article className={styles.card}>
          <h2>User profile</h2>
          {profileLoading ? <p>Loading profile…</p> : null}
          {profileError ? <p className={styles.error}>{profileError}</p> : null}
          {user ? (
            <form className={styles.form} onSubmit={handleProfileSave}>
              <label>
                <span>Email</span>
                <input value={user.email ?? ""} disabled readOnly />
              </label>
              <label>
                <span>Home city</span>
                <input
                  value={homeCity}
                  onChange={(event) => setHomeCity(event.target.value)}
                  placeholder="Chicago"
                />
              </label>
              <button type="submit" disabled={profileSaving}>
                {profileSaving ? "Saving…" : "Save profile"}
              </button>
            </form>
          ) : null}
        </article>

        <article className={styles.card}>
          <h2>Seed restaurants</h2>
          <form className={styles.form} onSubmit={handleSeedSubmit}>
            <label>
              <span>Name</span>
              <input
                  value={seedForm.name}
                  disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                  onChange={(event) => setSeedForm((current) => ({ ...current, name: event.target.value }))}
                  required
                />
            </label>
            <label>
              <span>City</span>
              <input
                  value={seedForm.city}
                  disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                  onChange={(event) => setSeedForm((current) => ({ ...current, city: event.target.value }))}
                  required
                />
            </label>
            <label>
              <span>Sentiment</span>
              <select
                value={seedForm.sentiment}
                disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                onChange={(event) =>
                  setSeedForm((current) => ({
                    ...current,
                    sentiment: event.target.value as "love" | "dislike",
                  }))
                }
              >
                <option value="love">love</option>
                <option value="dislike">dislike</option>
              </select>
            </label>
            <label>
              <span>Notes</span>
              <textarea
                rows={4}
                value={seedForm.notes}
                disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                onChange={(event) => setSeedForm((current) => ({ ...current, notes: event.target.value }))}
                placeholder="warm, creative, neighborhood feel, not stuffy"
              />
            </label>
            <button type="submit" disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}>
              {seedSubmitting ? "Adding…" : seedsLoading ? "Refreshing…" : "Add seed restaurant"}
            </button>
          </form>

          {seedError ? <p className={styles.error}>{seedError}</p> : null}
          {seedsLoading ? <p>Loading seeds…</p> : null}
          <div className={styles.stack}>
            {seeds.map((seed) => (
              <div key={seed.id} className={styles.inlineCard}>
                <div className={styles.row}>
                  <div className={styles.seedHeader}>
                    <strong>{seed.name}</strong>
                    <span className={styles.badge}>{seed.sentiment}</span>
                  </div>
                  <button
                    type="button"
                    className={styles.deleteButton}
                    onClick={() => void handleDeleteSeed(seed.id)}
                    disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                  >
                    {deletingSeedId === seed.id ? "Deleting…" : "Delete"}
                  </button>
                </div>
                <p>{seed.city}</p>
                <p className={styles.subtle}>{seed.notes || "No notes"}</p>
              </div>
            ))}
            {!seedsLoading && seeds.length === 0 ? <p className={styles.subtle}>No seed restaurants yet.</p> : null}
          </div>
        </article>
      </section>

      <section className={styles.grid}>
        <article className={styles.card}>
          <div className={styles.row}>
            <h2>Taste profile</h2>
            <button type="button" onClick={handleGenerateTasteProfile} disabled={tasteLoading}>
              {tasteLoading ? "Generating…" : "Generate profile"}
            </button>
          </div>
          {tasteError ? <p className={styles.error}>{tasteError}</p> : null}
          {tasteProfile ? (
            <div className={styles.stack}>
              <p>{tasteProfile.summary}</p>
              <div>
                <h3>Vibe</h3>
                <p>{(tasteProfile.attributes_json.vibe ?? []).join(", ") || "No vibe signals yet."}</p>
              </div>
              <div>
                <h3>Food style</h3>
                <p>{(tasteProfile.attributes_json.food_style ?? []).join(", ") || "No food-style signals yet."}</p>
              </div>
              <div>
                <h3>Avoid</h3>
                <p>{(tasteProfile.attributes_json.avoid ?? []).join(", ") || "No clear avoidance signals yet."}</p>
              </div>
            </div>
          ) : (
            <p className={styles.subtle}>Generate a taste profile to see the summary and structured attributes.</p>
          )}
        </article>

        <article className={styles.card}>
          <h2>Recommendations</h2>
          <form className={styles.form} onSubmit={handleRecommendationSubmit}>
            <label>
              <span>Destination city</span>
              <input
                value={recommendationForm.city}
                disabled={recommendationLoading}
                onChange={(event) =>
                  setRecommendationForm((current) => ({
                    ...current,
                    city: event.target.value,
                  }))
                }
                required
              />
            </label>
            <label>
              <span>Meal type</span>
              <input
                value={recommendationForm.meal_type}
                disabled={recommendationLoading}
                onChange={(event) =>
                  setRecommendationForm((current) => ({
                    ...current,
                    meal_type: event.target.value,
                  }))
                }
                placeholder="dinner"
              />
            </label>
            <label>
              <span>Party size</span>
              <input
                type="number"
                min="1"
                value={recommendationForm.party_size}
                disabled={recommendationLoading}
                onChange={(event) =>
                  setRecommendationForm((current) => ({
                    ...current,
                    party_size: event.target.value,
                  }))
                }
                required
              />
            </label>
            <label>
              <span>Budget</span>
              <select
                value={recommendationForm.budget}
                disabled={recommendationLoading}
                onChange={(event) =>
                  setRecommendationForm((current) => ({
                    ...current,
                    budget: event.target.value,
                  }))
                }
              >
                <option value="$">$</option>
                <option value="$$">$$</option>
                <option value="$$$">$$$</option>
                <option value="$$$$">$$$$</option>
              </select>
            </label>
            <label>
              <span>Max distance (meters)</span>
              <input
                type="number"
                min="1"
                value={recommendationForm.max_distance_meters}
                disabled={recommendationLoading}
                onChange={(event) =>
                  setRecommendationForm((current) => ({
                    ...current,
                    max_distance_meters: event.target.value,
                  }))
                }
                required
              />
            </label>
            <label>
              <span>Transport mode</span>
              <input
                value={recommendationForm.transport_mode}
                disabled={recommendationLoading}
                onChange={(event) =>
                  setRecommendationForm((current) => ({
                    ...current,
                    transport_mode: event.target.value,
                  }))
                }
                placeholder="walk"
              />
            </label>
            <label>
              <span>Special request</span>
              <textarea
                rows={3}
                value={recommendationForm.special_request}
                disabled={recommendationLoading}
                onChange={(event) =>
                  setRecommendationForm((current) => ({
                    ...current,
                    special_request: event.target.value,
                  }))
                }
                placeholder="memorable but not too formal"
              />
            </label>
            <button type="submit" disabled={recommendationLoading}>
              {recommendationLoading ? "Generating…" : "Generate recommendations"}
            </button>
          </form>

          {recommendationError ? <p className={styles.error}>{recommendationError}</p> : null}
          <div className={styles.recommendationList}>
            {recommendations.map((recommendation) => (
              <RecommendationCard key={recommendation.id} recommendation={recommendation} />
            ))}
            {!recommendationLoading && recommendations.length === 0 ? (
              <p className={styles.subtle}>Generate recommendations to see ranked restaurant cards.</p>
            ) : null}
          </div>
        </article>
      </section>
    </main>
  );
}
