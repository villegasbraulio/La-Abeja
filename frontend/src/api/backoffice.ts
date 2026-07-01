import { apiClient } from "./client";
import type {
  BackofficeCategory,
  BackofficeBooking,
  BackofficeBookingPayload,
  BackofficeCustomer,
  BackofficeExperience,
  BackofficeExperiencePayload,
  BackofficeDashboard,
  BackofficeTimeSlot,
  BackofficeOrderActionPayload,
  BackofficeOrderDetail,
  BackofficeOrderListItem,
  BackofficePromoCode,
  BackofficePromoCodePayload,
  BackofficeTimeSlotPayload,
  BackofficeVarietal,
  BackofficeWineDetail,
  BackofficeWineListItem,
  BackofficeWinePayload,
  ReservationMetricsDashboard,
  SalesMetricsDashboard,
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
  salesMetrics: async (period: string): Promise<SalesMetricsDashboard> => {
    const response = await apiClient.get<SalesMetricsDashboard>(
      `/backoffice/sales-metrics/?period=${encodeURIComponent(period)}`,
    );
    return response.data;
  },
  reservationMetrics: async (period: string): Promise<ReservationMetricsDashboard> => {
    const response = await apiClient.get<ReservationMetricsDashboard>(
      `/backoffice/visits/reservation-metrics/?period=${encodeURIComponent(period)}`,
    );
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
  visits: {
    experiences: {
      list: async (): Promise<BackofficeExperience[]> => {
        const response = await apiClient.get<BackofficeExperience[]>("/backoffice/visits/experiences/");
        return response.data;
      },
      detail: async (experienceId: string): Promise<BackofficeExperience> => {
        const response = await apiClient.get<BackofficeExperience>(
          `/backoffice/visits/experiences/${experienceId}/`,
        );
        return response.data;
      },
      create: async (payload: BackofficeExperiencePayload): Promise<BackofficeExperience> => {
        const response = await apiClient.post<BackofficeExperience>(
          "/backoffice/visits/experiences/",
          payload,
        );
        return response.data;
      },
      update: async (
        experienceId: string,
        payload: BackofficeExperiencePayload,
      ): Promise<BackofficeExperience> => {
        const response = await apiClient.put<BackofficeExperience>(
          `/backoffice/visits/experiences/${experienceId}/`,
          payload,
        );
        return response.data;
      },
      remove: async (experienceId: string): Promise<void> => {
        await apiClient.delete(`/backoffice/visits/experiences/${experienceId}/`);
      },
    },
    slots: {
      list: async (params?: { experience?: string }): Promise<BackofficeTimeSlot[]> => {
        const searchParams = new URLSearchParams();
        if (params?.experience) {
          searchParams.set("experience", params.experience);
        }
        const suffix = searchParams.toString();
        const response = await apiClient.get<BackofficeTimeSlot[]>(
          `/backoffice/visits/slots/${suffix ? `?${suffix}` : ""}`,
        );
        return response.data;
      },
      detail: async (slotId: number): Promise<BackofficeTimeSlot> => {
        const response = await apiClient.get<BackofficeTimeSlot>(`/backoffice/visits/slots/${slotId}/`);
        return response.data;
      },
      create: async (payload: BackofficeTimeSlotPayload): Promise<BackofficeTimeSlot> => {
        const response = await apiClient.post<BackofficeTimeSlot>("/backoffice/visits/slots/", payload);
        return response.data;
      },
      update: async (
        slotId: number,
        payload: BackofficeTimeSlotPayload,
      ): Promise<BackofficeTimeSlot> => {
        const response = await apiClient.put<BackofficeTimeSlot>(
          `/backoffice/visits/slots/${slotId}/`,
          payload,
        );
        return response.data;
      },
      remove: async (slotId: number): Promise<void> => {
        await apiClient.delete(`/backoffice/visits/slots/${slotId}/`);
      },
    },
    bookings: {
      list: async (params?: {
        experience?: string;
        status?: string;
        search?: string;
      }): Promise<BackofficeBooking[]> => {
        const searchParams = new URLSearchParams();
        if (params?.experience) {
          searchParams.set("experience", params.experience);
        }
        if (params?.status) {
          searchParams.set("status", params.status);
        }
        if (params?.search) {
          searchParams.set("search", params.search);
        }
        const suffix = searchParams.toString();
        const response = await apiClient.get<BackofficeBooking[]>(
          `/backoffice/visits/bookings/${suffix ? `?${suffix}` : ""}`,
        );
        return response.data;
      },
      detail: async (bookingId: string): Promise<BackofficeBooking> => {
        const response = await apiClient.get<BackofficeBooking>(
          `/backoffice/visits/bookings/${bookingId}/`,
        );
        return response.data;
      },
      update: async (
        bookingId: string,
        payload: BackofficeBookingPayload,
      ): Promise<BackofficeBooking> => {
        const response = await apiClient.patch<BackofficeBooking>(
          `/backoffice/visits/bookings/${bookingId}/`,
          payload,
        );
        return response.data;
      },
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
    updateAction: async (
      orderId: string,
      payload: BackofficeOrderActionPayload,
    ): Promise<BackofficeOrderDetail> => {
      const response = await apiClient.patch<BackofficeOrderDetail>(
        `/backoffice/orders/${orderId}/action/`,
        payload,
      );
      return response.data;
    },
    exportCsv: async (): Promise<Blob> => {
      const response = await apiClient.get("/backoffice/orders/export.csv", {
        responseType: "blob",
      });
      return response.data;
    },
  },
  customers: {
    list: async (params?: { search?: string }): Promise<PaginatedResponse<BackofficeCustomer>> => {
      const searchParams = new URLSearchParams();
      if (params?.search) {
        searchParams.set("search", params.search);
      }
      const suffix = searchParams.toString();
      const response = await apiClient.get<PaginatedResponse<BackofficeCustomer>>(
        `/backoffice/customers/${suffix ? `?${suffix}` : ""}`,
      );
      return response.data;
    },
    exportCsv: async (): Promise<Blob> => {
      const response = await apiClient.get("/backoffice/customers/export.csv", {
        responseType: "blob",
      });
      return response.data;
    },
  },
  promoCodes: {
    list: async (): Promise<PaginatedResponse<BackofficePromoCode>> => {
      const response = await apiClient.get<PaginatedResponse<BackofficePromoCode>>(
        "/backoffice/promo-codes/",
      );
      return response.data;
    },
    create: async (payload: BackofficePromoCodePayload): Promise<BackofficePromoCode> => {
      const response = await apiClient.post<BackofficePromoCode>("/backoffice/promo-codes/", payload);
      return response.data;
    },
    update: async (
      promoCodeId: number,
      payload: Partial<BackofficePromoCodePayload>,
    ): Promise<BackofficePromoCode> => {
      const response = await apiClient.patch<BackofficePromoCode>(
        `/backoffice/promo-codes/${promoCodeId}/`,
        payload,
      );
      return response.data;
    },
    remove: async (promoCodeId: number): Promise<void> => {
      await apiClient.delete(`/backoffice/promo-codes/${promoCodeId}/`);
    },
  },
};
