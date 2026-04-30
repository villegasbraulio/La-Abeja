import { useQuery } from "@tanstack/react-query";
import { catalogApi } from "../api/catalog";
import type { CatalogFilters } from "../types/catalog";

export function useCatalog(filters: CatalogFilters = {}) {
  return useQuery({
    queryKey: ["catalog", filters],
    queryFn: () => catalogApi.list(filters),
  });
}

export function useFeaturedWines() {
  return useQuery({
    queryKey: ["featured-wines"],
    queryFn: catalogApi.featured,
  });
}

export function useCatalogCategories() {
  return useQuery({
    queryKey: ["catalog-categories"],
    queryFn: catalogApi.categories,
  });
}

export function useCatalogVarietals() {
  return useQuery({
    queryKey: ["catalog-varietals"],
    queryFn: catalogApi.varietals,
  });
}
