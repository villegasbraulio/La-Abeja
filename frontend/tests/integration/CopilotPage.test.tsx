import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { BackofficeCopilotPage } from "../../src/pages/Backoffice/CopilotPage";
import { aiApi } from "../../src/api/ai";

vi.mock("../../src/api/ai", () => ({
  aiApi: {
    copilotMessage: vi.fn(),
    overview: vi.fn(),
  },
}));

function renderWithProviders(ui: ReactNode) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <MemoryRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("BackofficeCopilotPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(aiApi.overview).mockResolvedValue({
      metrics: {
        open_tasks: 2,
        new_leads: 1,
        pending_approvals: 0,
        runs_needing_human: 1,
      },
      prompt_suggestions: [
        "Mostrame el stock bajo",
        "Decime las ventas de los últimos 30 días",
      ],
      recent_tasks: [],
      recent_leads: [],
      pending_approvals: [],
    });
  });

  it("renders the initial copilot guidance", () => {
    renderWithProviders(<BackofficeCopilotPage />);

    expect(screen.getByText(/AI Support & Operations Agent/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Mostrame el stock bajo/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/tareas abiertas/i)).toBeInTheDocument();
  });

  it("sends a message and renders the returned conversation state", async () => {
    const user = userEvent.setup();
    vi.mocked(aiApi.copilotMessage).mockResolvedValue({
      conversation: {
        id: "conv-1",
        channel: "backoffice",
        mode: "ops",
        status: "open",
        last_intent: "low_stock",
        summary: "Estos son los vinos con stock bajo.",
        metadata: {},
        created_at: "2026-05-27T18:00:00.000Z",
        updated_at: "2026-05-27T18:01:00.000Z",
        turns: [
          {
            id: "turn-1",
            role: "user",
            content: "Mostrame el stock bajo",
            citations: [],
            metadata: {},
            created_at: "2026-05-27T18:00:00.000Z",
          },
          {
            id: "turn-2",
            role: "assistant",
            content: "Estos son los vinos con stock bajo ahora mismo:\n- Gran Reserva",
            citations: [],
            metadata: { intent: "low_stock" },
            created_at: "2026-05-27T18:01:00.000Z",
          },
        ],
      },
      assistant_turn: {
        id: "turn-2",
        role: "assistant",
        content: "Estos son los vinos con stock bajo ahora mismo:\n- Gran Reserva",
        citations: [],
        metadata: { intent: "low_stock" },
        created_at: "2026-05-27T18:01:00.000Z",
      },
      run: {
        id: "run-1",
        agent_type: "ops",
        model: "gpt-4.1",
        status: "completed",
        intent: "low_stock",
        message_text: "Mostrame el stock bajo",
        response_text: "Estos son los vinos con stock bajo ahora mismo:\n- Gran Reserva",
        citations: [],
        metadata: {},
        confidence: 0.95,
        needs_human: false,
        prompt_version: "v1",
        created_at: "2026-05-27T18:00:00.000Z",
        updated_at: "2026-05-27T18:01:00.000Z",
        tool_executions: [
          {
            id: "tool-1",
            tool_name: "list_low_stock_items",
            risk_level: "read_only",
            status: "succeeded",
            input_payload: { limit: 5 },
            output_payload: {},
            latency_ms: 8,
            error: "",
            created_at: "2026-05-27T18:01:00.000Z",
          },
        ],
      },
    });

    renderWithProviders(<BackofficeCopilotPage />);

    await user.type(screen.getByLabelText(/mensaje/i), "Mostrame el stock bajo");
    await user.click(screen.getByRole("button", { name: /enviar al copilot/i }));

    await waitFor(() => {
      expect(aiApi.copilotMessage).toHaveBeenCalled();
    });
    expect(vi.mocked(aiApi.copilotMessage).mock.calls[0]?.[0]).toEqual({
      conversation_id: undefined,
      message: "Mostrame el stock bajo",
    });

    expect(screen.getByText(/Estos son los vinos con stock bajo/i)).toBeInTheDocument();
    expect(screen.getByText(/último intent:/i).parentElement).toHaveTextContent("low_stock");
    expect(screen.getByText(/gpt-4.1/i)).toBeInTheDocument();
    expect(screen.getByText(/list_low_stock_items/i)).toBeInTheDocument();
    expect(screen.getByText(/ver tareas ai/i)).toBeInTheDocument();
  });

  it("shows an error message when the copilot request fails", async () => {
    const user = userEvent.setup();
    vi.mocked(aiApi.copilotMessage).mockRejectedValue(new Error("request failed"));

    renderWithProviders(<BackofficeCopilotPage />);

    await user.type(screen.getByLabelText(/mensaje/i), "Que pedidos pendientes tengo hoy?");
    await user.click(screen.getByRole("button", { name: /enviar al copilot/i }));

    expect(await screen.findByText(/No pudimos consultar el agente por ahora/i)).toBeInTheDocument();
  });
});
