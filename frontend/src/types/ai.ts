export interface AIConversationTurn {
  id: string;
  role: "user" | "assistant" | "tool" | "system";
  content: string;
  citations: Array<{
    chunk_id?: number;
    document_id?: number;
    document_title?: string;
    section?: string;
  }>;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AIConversation {
  id: string;
  channel: string;
  mode: string;
  status: string;
  last_intent: string;
  summary: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  turns: AIConversationTurn[];
}

export interface AIToolExecution {
  id: string;
  tool_name: string;
  risk_level: string;
  status: string;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  latency_ms: number;
  error: string;
  created_at: string;
}

export interface AIAgentRun {
  id: string;
  agent_type: string;
  model: string;
  status: string;
  intent: string;
  message_text: string;
  response_text: string;
  citations: Array<Record<string, unknown>>;
  metadata: Record<string, unknown>;
  confidence: string | number | null;
  needs_human: boolean;
  prompt_version: string;
  created_at: string;
  updated_at: string;
  tool_executions: AIToolExecution[];
}

export interface AICopilotResponse {
  conversation: AIConversation;
  assistant_turn: AIConversationTurn;
  run: AIAgentRun;
}
