import { apiClient } from "./client";
import type {
  BackofficeCategory,
  BackofficeDashboard,
  BackofficeOrderDetail,
  BackofficeOrderListItem,
  BackofficeVarietal,
  BackofficeWineDetail,
  BackofficeWineListItem,
  BackofficeWinePayload,
} from "../types/backoffice";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const backofficeApi = {
  dashboard: async (): Promise<BackofficeDashboard> => {
    const response = await apiClient.get<BackofficeDashboard>("/backoffice/dashboard/");
    return response.data;
  },
  categories: {
    list: async (): Promise<BackofficeCategory[]> => {
      const response = await apiClient.get<BackofficeCategory[]>("/backoffice/categories/");
      return response.data;
    },
    create: async (
      payload: Omit<BackofficeCategory, "id" | "wines_count">,
    ): Promise<BackofficeCategory> => {
      const response = await apiClient.post<BackofficeCategory>("/backoffice/categories/", payload);
      return response.data;
    },
    update: async (
      categoryId: number,
      payload: Partial<Omit<BackofficeCategory, "id" | "wines_count">>,
    ): Promise<BackofficeCategory> => {
      const response = await apiClient.patch<BackofficeCategory>(
        `/backoffice/categories/${categoryId}/`,
        payload,
      );
      return response.data;
    },
    remove: async (categoryId: number): Promise<void> => {
      await apiClient.delete(`/backoffice/categories/${categoryId}/`);
    },
  },
  varietals: {
    list: async (): Promise<BackofficeVarietal[]> => {
      const response = await apiClient.get<BackofficeVarietal[]>("/backoffice/varietals/");
      return response.data;
    },
    create: async (
      payload: Omit<BackofficeVarietal, "id" | "wines_count">,
    ): Promise<BackofficeVarietal> => {
      const response = await apiClient.post<BackofficeVarietal>("/backoffice/varietals/", payload);
      return response.data;
    },
    update: async (
      varietalId: number,
      payload: Partial<Omit<BackofficeVarietal, "id" | "wines_count">>,
    ): Promise<BackofficeVarietal> => {
      const response = await apiClient.patch<BackofficeVarietal>(
        `/backoffice/varietals/${varietalId}/`,
        payload,
      );
      return response.data;
    },
    remove: async (varietalId: number): Promise<void> => {
      await apiClient.delete(`/backoffice/varietals/${varietalId}/`);
    },
  },
  wines: {
    list: async (params?: {
      search?: string;
      category?: number | null;
      varietal?: number | null;
      is_active?: boolean | null;
    }): Promise<PaginatedResponse<BackofficeWineListItem>> => {
      const searchParams = new URLSearchParams();
      if (params?.search) {
        searchParams.set("search", params.search);
      }
      if (params?.category) {
        searchParams.set("category", String(params.category));
      }
      if (params?.varietal) {
        searchParams.set("varietal", String(params.varietal));
      }
      if (typeof params?.is_active === "boolean") {
        searchParams.set("is_active", String(params.is_active));
      }
      const suffix = searchParams.toString();
      const response = await apiClient.get<PaginatedResponse<BackofficeWineListItem>>(
        `/backoffice/wines/${suffix ? `?${suffix}` : ""}`,
      );
      return response.data;
    },
    detail: async (wineId: string): Promise<BackofficeWineDetail> => {
      const response = await apiClient.get<BackofficeWineDetail>(`/backoffice/wines/${wineId}/`);
      return response.data;
    },
    create: async (payload: BackofficeWinePayload): Promise<BackofficeWineDetail> => {
      const response = await apiClient.post<BackofficeWineDetail>("/backoffice/wines/", payload);
      return response.data;
    },
    update: async (
      wineId: string,
      payload: Partial<BackofficeWinePayload>,
    ): Promise<BackofficeWineDetail> => {
      const response = await apiClient.patch<BackofficeWineDetail>(
        `/backoffice/wines/${wineId}/`,
        payload,
      );
      return response.data;
    },
    remove: async (wineId: string): Promise<void> => {
      await apiClient.delete(`/backoffice/wines/${wineId}/`);
    },
  },
  orders: {
    list: async (params?: {
      search?: string;
      status?: string | null;
    }): Promise<PaginatedResponse<BackofficeOrderListItem>> => {
      const searchParams = new URLSearchParams();
      if (params?.search) {
        searchParams.set("search", params.search);
      }
      if (params?.status) {
        searchParams.set("status", params.status);
      }
      const suffix = searchParams.toString();
      const response = await apiClient.get<PaginatedResponse<BackofficeOrderListItem>>(
        `/backoffice/orders/${suffix ? `?${suffix}` : ""}`,
      );
      return response.data;
    },
    detail: async (orderId: string): Promise<BackofficeOrderDetail> => {
      const response = await apiClient.get<BackofficeOrderDetail>(`/backoffice/orders/${orderId}/`);
      return response.data;
    },
  },
};
