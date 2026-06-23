import { apiClient } from "./client";
import type {
  Order,
  OrderCreatePayload,
  ShippingQuoteRequestPayload,
  ShippingQuoteResponse,
} from "../types/orders";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const ordersApi = {
  quoteShipping: async (payload: ShippingQuoteRequestPayload): Promise<ShippingQuoteResponse> => {
    const response = await apiClient.post<ShippingQuoteResponse>("/orders/shipping-quotes/", payload);
    return response.data;
  },
  list: async (): Promise<PaginatedResponse<Order>> => {
    const response = await apiClient.get<PaginatedResponse<Order>>("/orders/orders/");
    return response.data;
  },
  create: async (payload: OrderCreatePayload): Promise<Order> => {
    const response = await apiClient.post<Order>("/orders/orders/", payload);
    return response.data;
  },
  detail: async (orderId: string, guestAccessToken?: string | null): Promise<Order> => {
    const response = await apiClient.get<Order>(`/orders/orders/${orderId}/`, {
      params: guestAccessToken ? { guest_access_token: guestAccessToken } : undefined,
    });
    return response.data;
  },
  cancel: async (orderId: string, guestAccessToken?: string | null): Promise<Order> => {
    const response = await apiClient.post<Order>(
      `/orders/orders/${orderId}/cancel/`,
      null,
      {
        params: guestAccessToken ? { guest_access_token: guestAccessToken } : undefined,
      },
    );
    return response.data;
  },
};
