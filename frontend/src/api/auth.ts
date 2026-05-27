import { apiClient } from "./client";
import type { AuthSession, AuthUser } from "../types/auth";

export const authApi = {
  register: async (payload: {
    email: string;
    first_name: string;
    last_name: string;
    password: string;
    phone?: string;
    newsletter_subscribed?: boolean;
    preferred_varietals?: string[];
  }): Promise<AuthSession> => {
    const response = await apiClient.post<AuthSession>("/auth/register/", payload);
    return response.data;
  },
  login: async (payload: { email: string; password: string }): Promise<AuthSession> => {
    const response = await apiClient.post<AuthSession>("/auth/login/", payload);
    return response.data;
  },
  profile: async (): Promise<AuthUser> => {
    const response = await apiClient.get<AuthUser>("/auth/profile/");
    return response.data;
  },
  logout: async (refreshToken: string): Promise<void> => {
    await apiClient.post("/auth/logout/", { refresh: refreshToken });
  },
};
