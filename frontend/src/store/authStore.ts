import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AuthUser } from "../types/auth";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: AuthUser | null;
  setTokens: (accessToken: string, refreshToken: string, user?: AuthUser | null) => void;
  setSession: (session: {
    accessToken: string;
    refreshToken: string;
    user: AuthUser;
  }) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      setTokens: (accessToken, refreshToken, user) =>
        set((state) => ({
          accessToken,
          refreshToken,
          user: user ?? state.user,
        })),
      setSession: ({ accessToken, refreshToken, user }) =>
        set({
          accessToken,
          refreshToken,
          user,
        }),
      logout: () => set({ accessToken: null, refreshToken: null, user: null }),
    }),
    {
      name: "bodega-la-abeja-auth",
    },
  ),
);
