"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  Recommendation,
  RecommendationFeedbackType,
  SeedPlaceCandidate,
  SeedRestaurant,
  TasteProfile,
  User,
  createSeed,
  deleteSeed,
  generateRecommendations,
  generateTasteProfile,
  getMe,
  getSeeds,
  searchSeedPlaces,
  setTemporaryUserId,
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
  budget: "$$",
  max_distance_meters: "2000",
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

function previewSeedTraits(seed: SeedRestaurant | SeedPlaceCandidate | null): string[] {
  if (!seed || !seed.derived_traits_json || typeof seed.derived_traits_json !== "object") {
    return [];
  }

  const traits = seed.derived_traits_json as Record<string, unknown>;
  const preview: string[] = [];
  for (const key of ["vibe", "food_style", "cuisine_style", "social_feel"]) {
    const values = traits[key];
    if (Array.isArray(values)) {
      for (const value of values) {
        const label = String(value).replace(/_/g, " ");
        if (!preview.includes(label)) {
          preview.push(label);
        }
        if (preview.length >= 4) {
          return preview;
        }
      }
    }
  }
  return preview;
}

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

function formatSeedEnrichmentStatus(seed: SeedRestaurant): string {
  if (!seed.is_verified_place) {
    return "Manual entry • lower confidence";
  }

  if (seed.enrichment_status === "ai_completed") {
    return "Verified place • AI-enriched";
  }

  if (seed.enrichment_status === "deterministic_only") {
    return "Verified place • enriched";
  }

  if (seed.enrichment_status) {
    return `Verified place • ${seed.enrichment_status}`;
  }

  return "Verified place";
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
  const [seedSearchLoading, setSeedSearchLoading] = useState(false);
  const [seedSearchPerformed, setSeedSearchPerformed] = useState(false);
  const [seedCandidates, setSeedCandidates] = useState<SeedPlaceCandidate[]>([]);
  const [selectedSeedCandidate, setSelectedSeedCandidate] = useState<SeedPlaceCandidate | null>(null);
  const [seedError, setSeedError] = useState<string | null>(null);

  const [tasteProfile, setTasteProfile] = useState<TasteProfile | null>(null);
  const [tasteLoading, setTasteLoading] = useState(false);
  const [tasteError, setTasteError] = useState<string | null>(null);

  const [recommendationForm, setRecommendationForm] = useState(initialRecommendationForm);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [recommendationError, setRecommendationError] = useState<string | null>(null);
  const [fallbackWarning, setFallbackWarning] = useState<string | null>(null);

  function handleSeedCandidateSelect(candidate: SeedPlaceCandidate) {
    setSelectedSeedCandidate(candidate);
    setSeedForm((current) => ({
      ...current,
      name: candidate.name,
      city: candidate.city,
    }));
    setSeedCandidates([]);
    setSeedSearchPerformed(false);
  }

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
        const tempUserId = crypto.randomUUID();
        setTemporaryUserId(tempUserId);
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
    return () => {
      setTemporaryUserId(null);
    };
  }, []);

  useEffect(() => {
    const city = seedForm.city.trim();
    const name = seedForm.name.trim();

    if (!city || name.length < 2) {
      setSeedSearchLoading(false);
      setSeedSearchPerformed(false);
      setSeedCandidates([]);
      return;
    }

    let cancelled = false;
    const timeoutId = window.setTimeout(() => {
      async function loadSeedCandidates() {
        try {
          setSeedSearchLoading(true);
          setSeedError(null);
          setSeedSearchPerformed(true);
          const candidates = await searchSeedPlaces({ name, city });
          if (!cancelled) {
            setSeedCandidates(candidates);
          }
        } catch (error) {
          if (!cancelled) {
            setSeedCandidates([]);
            setSeedError(error instanceof Error ? error.message : "Failed to search places");
          }
        } finally {
          if (!cancelled) {
            setSeedSearchLoading(false);
          }
        }
      }

      void loadSeedCandidates();
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [seedForm.city, seedForm.name]);

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
        source: selectedSeedCandidate?.source ?? null,
        source_place_id: selectedSeedCandidate?.source_place_id ?? null,
        formatted_address: selectedSeedCandidate?.formatted_address ?? null,
        lat: selectedSeedCandidate?.lat ?? null,
        lon: selectedSeedCandidate?.lon ?? null,
        price_level: selectedSeedCandidate?.price_level ?? null,
        rating: selectedSeedCandidate?.rating ?? null,
        user_ratings_total: selectedSeedCandidate?.user_ratings_total ?? null,
        raw_types: selectedSeedCandidate?.raw_types ?? null,
        review_summary_text: selectedSeedCandidate?.review_summary_text ?? null,
        editorial_summary_text: selectedSeedCandidate?.editorial_summary_text ?? null,
        menu_summary_text: selectedSeedCandidate?.menu_summary_text ?? null,
        raw_seed_note_text: seedForm.notes.trim() || null,
        raw_place_metadata_json: selectedSeedCandidate?.raw_place_metadata_json ?? null,
        raw_review_text: selectedSeedCandidate?.raw_review_text ?? null,
        derived_traits_json: selectedSeedCandidate?.derived_traits_json ?? null,
        ai_summary_text: selectedSeedCandidate?.ai_summary_text ?? null,
        place_traits_json: selectedSeedCandidate?.place_traits_json ?? null,
        is_verified_place: selectedSeedCandidate !== null,
      });
      await refreshSeeds();
      setSeedForm(initialSeedForm);
      setSeedCandidates([]);
      setSelectedSeedCandidate(null);
      setSeedSearchPerformed(false);
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
      setFallbackWarning(null);
      const response = await generateRecommendations({
        location: {
          city: recommendationForm.city.trim(),
        },
        context: {
          budget: recommendationForm.budget,
          max_distance_meters: Number(recommendationForm.max_distance_meters),
          special_request: recommendationForm.special_request,
        },
      });
      setRecommendations(response.recommendations);
      if (response.recommendations.some((item) => item.restaurant_json.source === "fallback_mock")) {
        setFallbackWarning("Google Places results were unavailable or insufficient, so fallback restaurant candidates are being shown.");
      }
    } catch (error) {
      setRecommendationError(error instanceof Error ? error.message : "Failed to generate recommendations");
      setFallbackWarning(null);
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
        </div>
      </section>

      <section className={styles.grid}>
        <article className={styles.card}>
          <h2>User profile</h2>
          {profileLoading ? <p>Loading profile…</p> : null}
          {profileError ? <p className={styles.error}>{profileError}</p> : null}
          {user ? (
            <form className={styles.form} onSubmit={handleProfileSave}>
              <p className={styles.subtle}>This session is temporary. Refreshing the page starts a new profile.</p>
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
              <span>City</span>
              <input
                  value={seedForm.city}
                  disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                  onChange={(event) => {
                    setSeedForm((current) => ({ ...current, city: event.target.value }));
                    setSelectedSeedCandidate(null);
                    setSeedCandidates([]);
                    setSeedSearchPerformed(false);
                  }}
                  required
                />
            </label>
            <label className={styles.autocompleteField}>
              <span>Name</span>
              <input
                  value={seedForm.name}
                  disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                  onChange={(event) => {
                    setSeedForm((current) => ({ ...current, name: event.target.value }));
                    setSelectedSeedCandidate(null);
                    setSeedCandidates([]);
                    setSeedSearchPerformed(false);
                  }}
                  required
                />
              {seedCandidates.length > 0 ? (
                <div className={styles.candidateDropdown}>
                  {seedCandidates.map((candidate) => (
                    <button
                      key={candidate.source_place_id}
                      type="button"
                      className={`${styles.candidateButton} ${
                        selectedSeedCandidate?.source_place_id === candidate.source_place_id ? styles.candidateButtonSelected : ""
                      }`}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => handleSeedCandidateSelect(candidate)}
                      disabled={seedSubmitting}
                    >
                      <strong>{candidate.name}</strong>
                      <span>{candidate.formatted_address || candidate.city}</span>
                    </button>
                  ))}
                </div>
              ) : null}
            </label>
            {selectedSeedCandidate ? (
              <div className={styles.seedHintBlock}>
                <p className={styles.feedbackSaved}>
                  Verified place selected: {selectedSeedCandidate.name}
                </p>
                {previewSeedTraits(selectedSeedCandidate).length ? (
                  <p className={styles.subtle}>
                    Trait preview: {previewSeedTraits(selectedSeedCandidate).join(", ")}
                  </p>
                ) : null}
              </div>
            ) : (
              <p className={styles.subtle}>
                Enter the city first, then type the restaurant name. Selecting a verified place gives stronger taste signals even if notes are brief.
              </p>
            )}
            {seedSearchLoading ? <p className={styles.subtle}>Searching places…</p> : null}
            {seedSearchPerformed && !seedSearchLoading && seedCandidates.length === 0 ? (
              <p className={styles.subtle}>No strong Google Places matches found. You can still save manually.</p>
            ) : null}
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
                <p className={styles.subtle}>{formatSeedEnrichmentStatus(seed)}</p>
                {seed.formatted_address ? <p className={styles.subtle}>{seed.formatted_address}</p> : null}
                {previewSeedTraits(seed).length ? (
                  <p className={styles.subtle}>Traits: {previewSeedTraits(seed).join(", ")}</p>
                ) : null}
                {seed.ai_summary_text ? <p className={styles.subtle}>{seed.ai_summary_text}</p> : null}
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
          {fallbackWarning ? <p className={styles.fallbackWarning}>{fallbackWarning}</p> : null}
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
