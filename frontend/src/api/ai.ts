import { apiClient } from "./client";
import type { AICopilotResponse } from "../types/ai";

export const aiApi = {
  copilotMessage: async (payload: {
    conversation_id?: string;
    message: string;
  }): Promise<AICopilotResponse> => {
    const response = await apiClient.post<AICopilotResponse>("/ai/copilot/messages/", payload);
    return response.data;
  },
};
