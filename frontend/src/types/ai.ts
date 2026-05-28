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

export interface AITask {
  id: string;
  task_type: string;
  title: string;
  description: string;
  status: string;
  priority: string;
  order: string | null;
  order_number: string | null;
  conversation: string | null;
  customer_email: string | null;
  customer_name: string | null;
  assigned_to_email: string | null;
  assigned_to_name: string | null;
  workflow_run: string | null;
  workflow_type: string | null;
  due_at: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AILead {
  id: string;
  full_name: string;
  email: string;
  phone: string;
  company: string;
  source_channel: string;
  status: string;
  interest_summary: string;
  desired_varietals: string[];
  estimated_order_value: string | null;
  conversation: string | null;
  customer_email: string | null;
  customer_name: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AIApproval {
  id: string;
  workflow_run: string;
  workflow_type: string;
  workflow_status: string | null;
  workflow_result: Record<string, unknown>;
  action_name: string;
  action_payload: Record<string, unknown>;
  status: string;
  approved_by: string | null;
  approved_by_email: string | null;
  decision_note: string;
  decided_at: string | null;
  created_at: string;
}

export interface AICopilotOverview {
  metrics: {
    open_tasks: number;
    new_leads: number;
    pending_approvals: number;
    runs_needing_human: number;
  };
  prompt_suggestions: string[];
  recent_tasks: AITask[];
  recent_leads: AILead[];
  pending_approvals: AIApproval[];
}
