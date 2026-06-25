import { apiClient } from "./client";
import type {
  VisitBooking,
  VisitBookingCreatePayload,
  VisitBookingPreferenceResponse,
  VisitExperience,
  VisitTimeSlot,
} from "../types/visits";

export const visitsApi = {
  experiences: async (): Promise<VisitExperience[]> => {
    const response = await apiClient.get<VisitExperience[]>("/visits/experiences/");
    return response.data;
  },
  slots: async (params?: { experience?: string; guest_count?: number }): Promise<VisitTimeSlot[]> => {
    const response = await apiClient.get<VisitTimeSlot[]>("/visits/slots/", {
      params,
    });
    return response.data;
  },
  createBooking: async (
    payload: VisitBookingCreatePayload,
  ): Promise<VisitBookingPreferenceResponse> => {
    const response = await apiClient.post<VisitBookingPreferenceResponse>("/visits/bookings/", payload);
    return response.data;
  },
  bookingDetail: async (
    bookingId: string,
    guestAccessToken?: string | null,
  ): Promise<VisitBooking> => {
    const response = await apiClient.get<VisitBooking>(`/visits/bookings/${bookingId}/`, {
      params: guestAccessToken ? { guest_access_token: guestAccessToken } : undefined,
    });
    return response.data;
  },
  cancelBooking: async (
    bookingId: string,
    guestAccessToken?: string | null,
  ): Promise<VisitBooking> => {
    const response = await apiClient.post<VisitBooking>(
      `/visits/bookings/${bookingId}/cancel/`,
      null,
      {
        params: guestAccessToken ? { guest_access_token: guestAccessToken } : undefined,
      },
    );
    return response.data;
  },
};
