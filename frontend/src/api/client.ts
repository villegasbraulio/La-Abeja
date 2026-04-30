import axios, { AxiosError, type AxiosRequestConfig } from "axios";
import { useAuthStore } from "../store/authStore";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000/api/v1";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((request) => {
    if (error) {
      request.reject(error);
      return;
    }
    if (token) {
      request.resolve(token);
    }
  });
  failedQueue = [];
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: (token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            resolve(apiClient(originalRequest));
          },
          reject,
        });
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refreshToken = useAuthStore.getState().refreshToken;
      const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
        refresh: refreshToken,
      });
      const { access, refresh } = response.data as { access: string; refresh: string };
      useAuthStore.getState().setTokens(access, refresh);
      processQueue(null, access);
      if (originalRequest.headers) {
        originalRequest.headers.Authorization = `Bearer ${access}`;
      }
      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      useAuthStore.getState().logout();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  },
);

export { apiClient };
