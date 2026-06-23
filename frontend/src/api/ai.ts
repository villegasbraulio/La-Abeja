import { apiClient } from "./client";
import type {
  AIApproval,
  AICopilotOverview,
  AICopilotResponse,
  AIStockReservation,
  AITask,
} from "../types/ai";

export const aiApi = {
  copilotMessage: async (payload: {
    conversation_id?: string;
    message: string;
  }): Promise<AICopilotResponse> => {
    const response = await apiClient.post<AICopilotResponse>("/ai/copilot/messages/", payload);
    return response.data;
  },
  overview: async (): Promise<AICopilotOverview> => {
    const response = await apiClient.get<AICopilotOverview>("/ai/copilot/overview/");
    return response.data;
  },
  tasks: {
    list: async (params?: {
      status?: string;
      task_type?: string;
      search?: string;
      conversation_id?: string;
    }): Promise<AITask[]> => {
      const searchParams = new URLSearchParams();
      if (params?.status) {
        searchParams.set("status", params.status);
      }
      if (params?.task_type) {
        searchParams.set("task_type", params.task_type);
      }
      if (params?.search) {
        searchParams.set("search", params.search);
      }
      if (params?.conversation_id) {
        searchParams.set("conversation_id", params.conversation_id);
      }
      const suffix = searchParams.toString();
      const response = await apiClient.get<AITask[]>(`/ai/tasks/${suffix ? `?${suffix}` : ""}`);
      return response.data;
    },
    update: async (
      taskId: string,
      payload: {
        status?: string;
        priority?: string;
        assigned_to_email?: string;
        due_at?: string | null;
      },
    ): Promise<AITask> => {
      const response = await apiClient.patch<AITask>(`/ai/tasks/${taskId}/`, payload);
      return response.data;
    },
  },
  stockReservations: {
    list: async (params?: {
      status?: string;
      search?: string;
    }): Promise<AIStockReservation[]> => {
      const searchParams = new URLSearchParams();
      if (params?.status) {
        searchParams.set("status", params.status);
      }
      if (params?.search) {
        searchParams.set("search", params.search);
      }
      const suffix = searchParams.toString();
      const response = await apiClient.get<AIStockReservation[]>(
        `/ai/stock-reservations/${suffix ? `?${suffix}` : ""}`,
      );
      return response.data;
    },
  },
  approvals: {
    list: async (params?: { status?: string; action_name?: string }): Promise<AIApproval[]> => {
      const searchParams = new URLSearchParams();
      if (params?.status) {
        searchParams.set("status", params.status);
      }
      if (params?.action_name) {
        searchParams.set("action_name", params.action_name);
      }
      const suffix = searchParams.toString();
      const response = await apiClient.get<AIApproval[]>(
        `/ai/approvals/${suffix ? `?${suffix}` : ""}`,
      );
      return response.data;
    },
    detail: async (approvalId: string): Promise<AIApproval> => {
      const response = await apiClient.get<AIApproval>(`/ai/approvals/${approvalId}/`);
      return response.data;
    },
    approve: async (approvalId: string, note?: string): Promise<AIApproval> => {
      const response = await apiClient.post<AIApproval>(`/ai/approvals/${approvalId}/approve/`, {
        note,
      });
      return response.data;
    },
    reject: async (approvalId: string, note?: string): Promise<AIApproval> => {
      const response = await apiClient.post<AIApproval>(`/ai/approvals/${approvalId}/reject/`, {
        note,
      });
      return response.data;
    },
  },
};
