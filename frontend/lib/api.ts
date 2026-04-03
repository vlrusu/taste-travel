const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") || "http://127.0.0.1:8000/api/v1";

export type User = {
  id: string;
  email: string | null;
  home_city: string | null;
  onboarding_complete: boolean;
  created_at: string;
  updated_at: string;
};

export type SeedRestaurant = {
  id: string;
  user_id: string;
  name: string;
  city: string;
  sentiment: "love" | "dislike";
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type TasteProfile = {
  id: string;
  user_id: string;
  summary: string;
  attributes_json: {
    vibe?: string[];
    food_style?: string[];
    avoid?: string[];
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
};

export type Recommendation = {
  id: string;
  user_id: string;
  request_context_json: Record<string, unknown>;
  restaurant_json: {
    name: string;
    city: string;
    country?: string;
    price_level: string;
    cuisine_tags: string[];
    vibe_tags: string[];
    [key: string]: unknown;
  };
  score: number;
  why: string;
  anchors_json: {
    matched_traits?: string[];
    caution_traits?: string[];
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
};

export type RecommendationFeedbackType =
  | "perfect"
  | "not_my_vibe"
  | "too_formal"
  | "too_touristy"
  | "too_expensive";

type JsonRequestOptions = Omit<RequestInit, "body" | "headers"> & {
  headers?: HeadersInit;
  json?: unknown;
};

async function request<T>(path: string, options: JsonRequestOptions = {}): Promise<T> {
  const { headers, json, ...requestInit } = options;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...requestInit,
    headers: {
      ...(json === undefined ? {} : { "Content-Type": "application/json" }),
      ...(headers ?? {}),
    },
    body: json === undefined ? undefined : JSON.stringify(json),
    cache: "no-store",
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const payload = await response.json();
      message = payload.detail ?? JSON.stringify(payload);
    } catch {
      message = await response.text();
    }
    throw new Error(message || "Request failed");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function getMe() {
  return request<User>("/me");
}

export function updateMe(payload: { home_city: string | null }) {
  return request<User>("/me", {
    method: "PATCH",
    json: payload,
  });
}

export function getSeeds() {
  return request<SeedRestaurant[]>("/me/seeds");
}

export function createSeed(payload: {
  name: string;
  city: string;
  sentiment: "love" | "dislike";
  notes: string;
}) {
  return request<SeedRestaurant>("/me/seeds", {
    method: "POST",
    json: payload,
  });
}

export function deleteSeed(seedId: string) {
  return request<void>(`/me/seeds/${seedId}`, {
    method: "DELETE",
  });
}

export function generateTasteProfile() {
  return request<{ taste_profile: TasteProfile }>("/me/taste-profile:generate", {
    method: "POST",
  });
}

export function generateRecommendations(payload: {
  location: {
    city: string;
    lat?: number | null;
    lon?: number | null;
  };
  context: {
    meal_type: string;
    party_size: number;
    budget: string;
    max_distance_meters: number;
    transport_mode: string;
    special_request: string;
  };
}) {
  return request<{ recommendations: Recommendation[] }>("/recommendations:generate", {
    method: "POST",
    json: {
      location: {
        city: payload.location.city,
        ...(payload.location.lat == null ? {} : { lat: payload.location.lat }),
        ...(payload.location.lon == null ? {} : { lon: payload.location.lon }),
      },
      context: {
        meal_type: payload.context.meal_type || null,
        party_size: payload.context.party_size,
        budget: payload.context.budget || null,
        max_distance_meters: payload.context.max_distance_meters,
        transport_mode: payload.context.transport_mode || null,
        special_request: payload.context.special_request || null,
      },
    },
  });
}

export function submitRecommendationFeedback(
  recommendationId: string,
  feedbackType: RecommendationFeedbackType,
) {
  return request<{ id: string }>(`/recommendations/${recommendationId}/feedback`, {
    method: "POST",
    json: {
      feedback_type: feedbackType,
    },
  });
}
