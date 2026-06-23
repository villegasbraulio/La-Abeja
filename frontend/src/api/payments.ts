import { apiClient } from "./client";
import type { CheckoutPreferenceResponse } from "../types/payments";

export const paymentsApi = {
  createPreference: async (
    orderId: string,
    guestAccessToken?: string | null,
  ): Promise<CheckoutPreferenceResponse> => {
    const response = await apiClient.post<CheckoutPreferenceResponse>(
      "/payments/create-preference/",
      {
        order_id: orderId,
        guest_access_token: guestAccessToken ?? undefined,
      },
    );
    return response.data;
  },
};
