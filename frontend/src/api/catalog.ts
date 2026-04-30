import { apiClient } from "./client";
import type {
  CatalogCategory,
  CatalogFilters,
  CatalogResponse,
  CatalogVarietal,
  WineDetail,
  WineListItem,
} from "../types/catalog";

type FeaturedWinesResponse = WineListItem[] | CatalogResponse;

function isCatalogResponse(data: unknown): data is CatalogResponse {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const candidate = data as Partial<CatalogResponse>;
  return typeof candidate.count === "number" && Array.isArray(candidate.results);
}

function ensureCatalogResponse(data: unknown): CatalogResponse {
  if (!isCatalogResponse(data)) {
    throw new Error("Invalid catalog response shape.");
  }

  return data;
}

function isWineDetail(data: unknown): data is WineDetail {
  if (typeof data !== "object" || data === null) {
    return false;
  }

  const candidate = data as Partial<WineDetail>;
  return (
    typeof candidate.id === "string" &&
    typeof candidate.slug === "string" &&
    typeof candidate.name === "string" &&
    Array.isArray(candidate.images) &&
    Array.isArray(candidate.recent_reviews)
  );
}

export const catalogApi = {
  list: async (filters: CatalogFilters = {}): Promise<CatalogResponse> => {
    const params = new URLSearchParams();

    Object.entries(filters).forEach(([key, value]) => {
      if (value === undefined || value === null || value === "") {
        return;
      }

      params.set(key, String(value));
    });

    const suffix = params.toString();
    const response = await apiClient.get<unknown>(
      `/catalog/wines/${suffix ? `?${suffix}` : ""}`,
    );
    return ensureCatalogResponse(response.data);
  },
  featured: async (): Promise<WineListItem[]> => {
    const response = await apiClient.get<FeaturedWinesResponse>("/catalog/wines/featured/");
    if (Array.isArray(response.data)) {
      return response.data;
    }

    return ensureCatalogResponse(response.data).results;
  },
  detail: async (slug: string): Promise<WineDetail> => {
    const response = await apiClient.get<unknown>(`/catalog/wines/${slug}/`);
    if (!isWineDetail(response.data)) {
      throw new Error("Invalid wine detail response shape.");
    }
    return response.data;
  },
  categories: async (): Promise<CatalogCategory[]> => {
    const response = await apiClient.get<CatalogCategory[]>("/catalog/categories/");
    return response.data;
  },
  varietals: async (): Promise<CatalogVarietal[]> => {
    const response = await apiClient.get<CatalogVarietal[]>("/catalog/varietals/");
    return response.data;
  },
};
