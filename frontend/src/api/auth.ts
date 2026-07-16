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
  updateProfile: async (
    payload: Partial<
      Pick<
        AuthUser,
        | "first_name"
        | "last_name"
        | "phone"
        | "birth_date"
        | "avatar"
        | "preferred_varietals"
        | "newsletter_subscribed"
      >
    >,
  ): Promise<AuthUser> => {
    const response = await apiClient.patch<AuthUser>("/auth/profile/", payload);
    return response.data;
  },
  changePassword: async (payload: {
    old_password: string;
    new_password: string;
  }): Promise<{ detail: string }> => {
    const response = await apiClient.post<{ detail: string }>("/auth/password/change/", payload);
    return response.data;
  },
  logout: async (refreshToken: string): Promise<void> => {
    await apiClient.post("/auth/logout/", { refresh: refreshToken });
  },
};
