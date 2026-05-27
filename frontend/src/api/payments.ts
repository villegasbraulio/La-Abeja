import { apiClient } from "./client";
import type { CheckoutPreferenceResponse } from "../types/payments";

export const paymentsApi = {
  createPreference: async (orderId: string): Promise<CheckoutPreferenceResponse> => {
    const response = await apiClient.post<CheckoutPreferenceResponse>(
      "/payments/create-preference/",
      { order_id: orderId },
    );
    return response.data;
  },
};
