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
import {
  MapPin,
  Star,
  Sparkles,
  Plus,
  Trash2,
  ExternalLink,
  ThumbsUp,
  ThumbsDown,
  AlertCircle,
  ChefHat,
  Compass,
  User as UserIcon,
  Search,
  DollarSign,
  Clock,
} from "lucide-react";
import clsx from "clsx";

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
    return "Manual entry";
  }

  if (seed.enrichment_status === "ai_completed") {
    return "Verified & AI-enriched";
  }

  if (seed.enrichment_status === "deterministic_only") {
    return "Verified & enriched";
  }

  if (seed.enrichment_status) {
    return `Verified (${seed.enrichment_status})`;
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
    <div className="group rounded-xl border border-border bg-card p-5 transition-all duration-200 hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h3 className="mb-1 flex items-center gap-2 text-lg font-semibold text-card-foreground">
            <a
              href={mapsUrl}
              target="_blank"
              rel="noreferrer"
              className="transition-colors hover:text-primary"
            >
              {recommendation.restaurant_json.name}
            </a>
            <ExternalLink className="h-4 w-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
          </h3>
          <p className="flex items-center gap-1.5 text-sm text-muted-foreground">
            <MapPin className="h-3.5 w-3.5" />
            {recommendation.restaurant_json.city}
            {recommendation.restaurant_json.country ? `, ${recommendation.restaurant_json.country}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-secondary px-2.5 py-1 text-sm font-semibold text-secondary-foreground">
            {recommendation.restaurant_json.price_level}
          </span>
          <span className="flex items-center gap-1 rounded-md bg-primary/10 px-2.5 py-1 text-sm font-semibold text-primary">
            <Star className="h-3.5 w-3.5 fill-primary" />
            {recommendation.score.toFixed(1)}
          </span>
        </div>
      </div>

      <div className="mb-4 space-y-3">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Cuisine
          </p>
          <div className="flex flex-wrap gap-1.5">
            {recommendation.restaurant_json.cuisine_tags.map((tag) => (
              <span
                key={`${recommendation.id}-${tag}`}
                className="rounded-md bg-secondary px-2 py-0.5 text-xs text-secondary-foreground"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Vibe
          </p>
          <div className="flex flex-wrap gap-1.5">
            {recommendation.restaurant_json.vibe_tags.map((tag) => (
              <span
                key={`${recommendation.id}-vibe-${tag}`}
                className="rounded-md bg-primary/10 px-2 py-0.5 text-xs text-primary"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="mb-4 rounded-lg bg-muted/50 p-3">
        <p className="mb-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Why it fits
        </p>
        <p className="text-sm leading-relaxed text-card-foreground">{recommendation.why}</p>
      </div>

      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-lg border border-border/50 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <ThumbsUp className="h-3 w-3 text-green-500" />
            Matched traits
          </p>
          {recommendation.anchors_json.matched_traits?.length ? (
            <ul className="space-y-1 text-sm text-card-foreground">
              {recommendation.anchors_json.matched_traits.map((trait) => (
                <li key={`${recommendation.id}-match-${trait}`} className="flex items-center gap-1.5">
                  <span className="h-1 w-1 rounded-full bg-green-500" />
                  {trait}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No strong matches</p>
          )}
        </div>

        <div className="rounded-lg border border-border/50 p-3">
          <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            <AlertCircle className="h-3 w-3 text-amber-500" />
            Caution traits
          </p>
          {recommendation.anchors_json.caution_traits?.length ? (
            <ul className="space-y-1 text-sm text-card-foreground">
              {recommendation.anchors_json.caution_traits.map((trait) => (
                <li key={`${recommendation.id}-caution-${trait}`} className="flex items-center gap-1.5">
                  <span className="h-1 w-1 rounded-full bg-amber-500" />
                  {trait}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">No cautions</p>
          )}
        </div>
      </div>

      <div className="border-t border-border pt-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Quick feedback
        </p>
        <div className="flex flex-wrap gap-2">
          {feedbackOptions.map((option) => (
            <button
              key={`${recommendation.id}-${option.value}`}
              type="button"
              onClick={() => void handleFeedback(option.value)}
              disabled={feedbackLoading}
              className={clsx(
                "rounded-md border border-border px-3 py-1.5 text-sm transition-all",
                "hover:border-primary hover:bg-primary/10 hover:text-primary",
                "disabled:cursor-not-allowed disabled:opacity-50"
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
        {feedbackSaved && (
          <p className="mt-2 text-sm text-green-500">Feedback saved!</p>
        )}
        {feedbackError && (
          <p className="mt-2 text-sm text-destructive">{feedbackError}</p>
        )}
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
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      {/* Hero Section */}
      <section className="mb-10 rounded-2xl border border-border bg-gradient-to-br from-card via-card to-primary/5 p-8 sm:p-10">
        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <Compass className="h-5 w-5 text-primary" />
          </div>
          <span className="text-xs font-semibold uppercase tracking-widest text-primary">
            Taste Travel
          </span>
        </div>
        <h1 className="text-balance text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
          Restaurant recommendations shaped by your travel taste profile.
        </h1>
        <p className="mt-4 max-w-2xl text-lg text-muted-foreground">
          Tell us about restaurants you love, and we&apos;ll find your perfect spots anywhere in the world.
        </p>
      </section>

      {/* Profile & Seeds Grid */}
      <section className="mb-8 grid gap-6 lg:grid-cols-2">
        {/* User Profile Card */}
        <article className="rounded-xl border border-border bg-card p-6">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-secondary">
              <UserIcon className="h-4 w-4 text-secondary-foreground" />
            </div>
            <h2 className="text-lg font-semibold text-card-foreground">User Profile</h2>
          </div>

          {profileLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Loading profile...
            </div>
          ) : null}

          {profileError ? (
            <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{profileError}</p>
          ) : null}

          {user ? (
            <form onSubmit={handleProfileSave} className="space-y-4">
              <p className="text-sm text-muted-foreground">
                This session is temporary. Refreshing starts a new profile.
              </p>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
                  Home city
                </label>
                <input
                  value={homeCity}
                  onChange={(event) => setHomeCity(event.target.value)}
                  placeholder="Chicago"
                  className="w-full rounded-lg border border-border bg-input px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>
              <button
                type="submit"
                disabled={profileSaving}
                className={clsx(
                  "inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 font-medium text-primary-foreground transition-all",
                  "hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background",
                  "disabled:cursor-not-allowed disabled:opacity-50"
                )}
              >
                {profileSaving ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                    Saving...
                  </>
                ) : (
                  "Save profile"
                )}
              </button>
            </form>
          ) : null}
        </article>

        {/* Seed Restaurants Card */}
        <article className="rounded-xl border border-border bg-card p-6">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <ChefHat className="h-4 w-4 text-primary" />
            </div>
            <h2 className="text-lg font-semibold text-card-foreground">Seed Restaurants</h2>
          </div>

          <form onSubmit={handleSeedSubmit} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
                  City
                </label>
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
                  className="w-full rounded-lg border border-border bg-input px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
              <div className="relative">
                <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
                  Name
                </label>
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
                  className="w-full rounded-lg border border-border bg-input px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
                />
                {seedCandidates.length > 0 && (
                  <div className="absolute left-0 right-0 top-full z-10 mt-1 max-h-56 overflow-y-auto rounded-lg border border-border bg-card shadow-xl">
                    {seedCandidates.map((candidate) => (
                      <button
                        key={candidate.source_place_id}
                        type="button"
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => handleSeedCandidateSelect(candidate)}
                        disabled={seedSubmitting}
                        className={clsx(
                          "w-full px-4 py-3 text-left transition-colors hover:bg-secondary",
                          selectedSeedCandidate?.source_place_id === candidate.source_place_id && "bg-secondary"
                        )}
                      >
                        <strong className="block text-sm text-card-foreground">{candidate.name}</strong>
                        <span className="text-xs text-muted-foreground">
                          {candidate.formatted_address || candidate.city}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {selectedSeedCandidate ? (
              <div className="rounded-lg bg-primary/10 p-3">
                <p className="text-sm font-medium text-primary">
                  Verified place selected: {selectedSeedCandidate.name}
                </p>
                {previewSeedTraits(selectedSeedCandidate).length > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Traits: {previewSeedTraits(selectedSeedCandidate).join(", ")}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Enter city first, then type the restaurant name for verified matches.
              </p>
            )}

            {seedSearchLoading && (
              <p className="flex items-center gap-2 text-sm text-muted-foreground">
                <Search className="h-3.5 w-3.5 animate-pulse" />
                Searching places...
              </p>
            )}

            {seedSearchPerformed && !seedSearchLoading && seedCandidates.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No Google Places matches found. You can still save manually.
              </p>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
                  Sentiment
                </label>
                <select
                  value={seedForm.sentiment}
                  disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                  onChange={(event) =>
                    setSeedForm((current) => ({
                      ...current,
                      sentiment: event.target.value as "love" | "dislike",
                    }))
                  }
                  className="w-full rounded-lg border border-border bg-input px-4 py-2.5 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="love">Love it</option>
                  <option value="dislike">Dislike it</option>
                </select>
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
                Notes
              </label>
              <textarea
                rows={3}
                value={seedForm.notes}
                disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                onChange={(event) => setSeedForm((current) => ({ ...current, notes: event.target.value }))}
                placeholder="warm, creative, neighborhood feel, not stuffy"
                className="w-full rounded-lg border border-border bg-input px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>

            <button
              type="submit"
              disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
              className={clsx(
                "inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 font-medium text-primary-foreground transition-all",
                "hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background",
                "disabled:cursor-not-allowed disabled:opacity-50"
              )}
            >
              <Plus className="h-4 w-4" />
              {seedSubmitting ? "Adding..." : seedsLoading ? "Refreshing..." : "Add seed restaurant"}
            </button>
          </form>

          {seedError && (
            <p className="mt-4 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{seedError}</p>
          )}

          {seedsLoading ? (
            <div className="mt-4 flex items-center gap-2 text-muted-foreground">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              Loading seeds...
            </div>
          ) : null}

          <div className="mt-4 space-y-3">
            {seeds.map((seed) => (
              <div
                key={seed.id}
                className="group rounded-lg border border-border bg-muted/30 p-4 transition-colors hover:border-border/80"
              >
                <div className="mb-2 flex items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <strong className="text-card-foreground">{seed.name}</strong>
                    <span
                      className={clsx(
                        "rounded-md px-2 py-0.5 text-xs font-medium",
                        seed.sentiment === "love"
                          ? "bg-green-500/10 text-green-500"
                          : "bg-red-500/10 text-red-500"
                      )}
                    >
                      {seed.sentiment}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleDeleteSeed(seed.id)}
                    disabled={seedSubmitting || seedsLoading || deletingSeedId !== null}
                    className="rounded-md p-1.5 text-muted-foreground opacity-0 transition-all hover:bg-destructive/10 hover:text-destructive group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <p className="text-sm text-muted-foreground">{seed.city}</p>
                <p className="text-xs text-muted-foreground">{formatSeedEnrichmentStatus(seed)}</p>
                {seed.formatted_address && (
                  <p className="text-xs text-muted-foreground">{seed.formatted_address}</p>
                )}
                {previewSeedTraits(seed).length > 0 && (
                  <p className="mt-1 text-xs text-muted-foreground">
                    Traits: {previewSeedTraits(seed).join(", ")}
                  </p>
                )}
                {seed.ai_summary_text && (
                  <p className="mt-1 text-xs text-muted-foreground">{seed.ai_summary_text}</p>
                )}
                <p className="mt-1 text-xs text-muted-foreground">{seed.notes || "No notes"}</p>
              </div>
            ))}
            {!seedsLoading && seeds.length === 0 && (
              <p className="text-center text-sm text-muted-foreground">No seed restaurants yet.</p>
            )}
          </div>
        </article>
      </section>

      {/* Taste Profile & Recommendations Grid */}
      <section className="grid gap-6 lg:grid-cols-2">
        {/* Taste Profile Card */}
        <article className="rounded-xl border border-border bg-card p-6">
          <div className="mb-5 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
                <Sparkles className="h-4 w-4 text-primary" />
              </div>
              <h2 className="text-lg font-semibold text-card-foreground">Taste Profile</h2>
            </div>
            <button
              type="button"
              onClick={handleGenerateTasteProfile}
              disabled={tasteLoading}
              className={clsx(
                "inline-flex items-center gap-2 rounded-lg border border-primary bg-transparent px-4 py-2 text-sm font-medium text-primary transition-all",
                "hover:bg-primary hover:text-primary-foreground",
                "disabled:cursor-not-allowed disabled:opacity-50"
              )}
            >
              {tasteLoading ? (
                <>
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="h-3.5 w-3.5" />
                  Generate
                </>
              )}
            </button>
          </div>

          {tasteError && (
            <p className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">{tasteError}</p>
          )}

          {tasteProfile ? (
            <div className="space-y-4">
              <p className="rounded-lg bg-muted/50 p-4 text-sm leading-relaxed text-card-foreground">
                {tasteProfile.summary}
              </p>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="rounded-lg border border-border/50 p-3">
                  <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Vibe
                  </h3>
                  <p className="text-sm text-card-foreground">
                    {(tasteProfile.attributes_json.vibe ?? []).join(", ") || "No vibe signals"}
                  </p>
                </div>
                <div className="rounded-lg border border-border/50 p-3">
                  <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Food Style
                  </h3>
                  <p className="text-sm text-card-foreground">
                    {(tasteProfile.attributes_json.food_style ?? []).join(", ") || "No food-style signals"}
                  </p>
                </div>
                <div className="rounded-lg border border-border/50 p-3">
                  <h3 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                    Avoid
                  </h3>
                  <p className="text-sm text-card-foreground">
                    {(tasteProfile.attributes_json.avoid ?? []).join(", ") || "No avoidance signals"}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Generate a taste profile to see the summary and structured attributes.
            </p>
          )}
        </article>

        {/* Recommendations Card */}
        <article className="rounded-xl border border-border bg-card p-6">
          <div className="mb-5 flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
              <MapPin className="h-4 w-4 text-primary" />
            </div>
            <h2 className="text-lg font-semibold text-card-foreground">Recommendations</h2>
          </div>

          <form onSubmit={handleRecommendationSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
                Destination city
              </label>
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
                placeholder="Paris, Tokyo, New York..."
                className="w-full rounded-lg border border-border bg-input px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
                  <DollarSign className="h-3.5 w-3.5" />
                  Budget
                </label>
                <select
                  value={recommendationForm.budget}
                  disabled={recommendationLoading}
                  onChange={(event) =>
                    setRecommendationForm((current) => ({
                      ...current,
                      budget: event.target.value,
                    }))
                  }
                  className="w-full rounded-lg border border-border bg-input px-4 py-2.5 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="$">$ - Budget</option>
                  <option value="$$">$$ - Moderate</option>
                  <option value="$$$">$$$ - Upscale</option>
                  <option value="$$$$">$$$$ - Fine Dining</option>
                </select>
              </div>

              <div>
                <label className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
                  <Clock className="h-3.5 w-3.5" />
                  Max distance (meters)
                </label>
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
                  className="w-full rounded-lg border border-border bg-input px-4 py-2.5 text-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-muted-foreground">
                Special request
              </label>
              <textarea
                rows={2}
                value={recommendationForm.special_request}
                disabled={recommendationLoading}
                onChange={(event) =>
                  setRecommendationForm((current) => ({
                    ...current,
                    special_request: event.target.value,
                  }))
                }
                placeholder="memorable but not too formal"
                className="w-full rounded-lg border border-border bg-input px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary disabled:cursor-not-allowed disabled:opacity-50"
              />
            </div>

            <button
              type="submit"
              disabled={recommendationLoading}
              className={clsx(
                "inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 font-medium text-primary-foreground transition-all",
                "hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 focus:ring-offset-background",
                "disabled:cursor-not-allowed disabled:opacity-50"
              )}
            >
              {recommendationLoading ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  Generate recommendations
                </>
              )}
            </button>
          </form>

          {recommendationError && (
            <p className="mt-4 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              {recommendationError}
            </p>
          )}

          {fallbackWarning && (
            <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/10 p-3">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
              <p className="text-sm text-amber-500">{fallbackWarning}</p>
            </div>
          )}

          <div className="mt-6 space-y-4">
            {recommendations.map((recommendation) => (
              <RecommendationCard key={recommendation.id} recommendation={recommendation} />
            ))}
            {!recommendationLoading && recommendations.length === 0 && (
              <p className="py-8 text-center text-sm text-muted-foreground">
                Generate recommendations to see ranked restaurant cards.
              </p>
            )}
          </div>
        </article>
      </section>
    </main>
  );
}
