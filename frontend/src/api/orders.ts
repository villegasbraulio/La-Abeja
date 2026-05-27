import { apiClient } from "./client";
import type { Order, OrderCreatePayload } from "../types/orders";

interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const ordersApi = {
  list: async (): Promise<PaginatedResponse<Order>> => {
    const response = await apiClient.get<PaginatedResponse<Order>>("/orders/orders/");
    return response.data;
  },
  create: async (payload: OrderCreatePayload): Promise<Order> => {
    const response = await apiClient.post<Order>("/orders/orders/", payload);
    return response.data;
  },
  detail: async (orderId: string): Promise<Order> => {
    const response = await apiClient.get<Order>(`/orders/orders/${orderId}/`);
    return response.data;
  },
  cancel: async (orderId: string): Promise<Order> => {
    const response = await apiClient.post<Order>(`/orders/orders/${orderId}/cancel/`);
    return response.data;
  },
};
