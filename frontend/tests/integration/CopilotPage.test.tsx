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
    approvals: {
      detail: vi.fn(),
      approve: vi.fn(),
      reject: vi.fn(),
    },
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
        pending_approvals: 0,
        runs_needing_human: 1,
        active_stock_reservations: 1,
        pending_cancellation_approvals: 1,
      },
      prompt_suggestions: [
        "Mostrame el stock bajo",
        "Decime las ventas de los últimos 30 días",
      ],
      recent_tasks: [],
      recent_stock_reservations: [],
      pending_approvals: [],
      pending_cancellation_approvals: [],
    });
    vi.mocked(aiApi.approvals.detail).mockResolvedValue({
      id: "approval-1",
      workflow_run: "workflow-1",
      workflow_type: "tool_approval",
      workflow_status: "pending",
      workflow_result: {},
      action_name: "reserve_stock",
      action_payload: {
        order_number: "LAB-2026-000145",
        quantity: 3,
        sku: "LAB-RES-900",
      },
      status: "pending",
      approved_by: null,
      approved_by_email: null,
      decision_note: "",
      decided_at: null,
      created_at: "2026-05-29T18:00:00.000Z",
    });
  });

  it("renders the initial copilot guidance", () => {
    renderWithProviders(<BackofficeCopilotPage />);

    expect(screen.getByText(/Asistente de soporte y operaciones/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Mostrame el stock bajo/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/tareas abiertas/i)).toBeInTheDocument();
    expect(screen.getByText(/reservas activas/i)).toBeInTheDocument();
    expect(screen.getByText(/acciones disponibles/i)).toBeInTheDocument();
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
    expect(screen.getAllByText(/ver tareas/i).length).toBeGreaterThan(0);
  });

  it("loads a quick action prompt into the textarea", async () => {
    const user = userEvent.setup();

    renderWithProviders(<BackofficeCopilotPage />);

    await user.click(screen.getAllByRole("button", { name: /cargar prompt/i })[0]);

    expect(screen.getByLabelText(/mensaje/i)).toHaveValue("Traeme el 360 del cliente ana@example.com");
  });

  it("shows an error message when the copilot request fails", async () => {
    const user = userEvent.setup();
    vi.mocked(aiApi.copilotMessage).mockRejectedValue(new Error("request failed"));

    renderWithProviders(<BackofficeCopilotPage />);

    await user.type(screen.getByLabelText(/mensaje/i), "Que pedidos pendientes tengo hoy?");
    await user.click(screen.getByRole("button", { name: /enviar al copilot/i }));

    expect(await screen.findByText(/No pudimos consultar el agente por ahora/i)).toBeInTheDocument();
  });

  it("lets the operator approve a blocked action directly from Copilot", async () => {
    const user = userEvent.setup();
    vi.mocked(aiApi.copilotMessage).mockResolvedValue({
      conversation: {
        id: "conv-approval",
        channel: "backoffice",
        mode: "ops",
        status: "open",
        last_intent: "reserve_stock",
        summary: "Prepare la operacion de stock, pero requiere aprobacion humana antes de ejecutarse.",
        metadata: {},
        created_at: "2026-05-29T18:00:00.000Z",
        updated_at: "2026-05-29T18:01:00.000Z",
        turns: [
          {
            id: "turn-user",
            role: "user",
            content: "Reservá 3 unidades del SKU LAB-RES-900 para LAB-2026-000145",
            citations: [],
            metadata: {},
            created_at: "2026-05-29T18:00:00.000Z",
          },
          {
            id: "turn-assistant",
            role: "assistant",
            content: "Prepare la operacion de stock, pero requiere aprobacion humana antes de ejecutarse. Approval approval-1.",
            citations: [],
            metadata: { intent: "reserve_stock" },
            created_at: "2026-05-29T18:01:00.000Z",
          },
        ],
      },
      assistant_turn: {
        id: "turn-assistant",
        role: "assistant",
        content: "Prepare la operacion de stock, pero requiere aprobacion humana antes de ejecutarse. Approval approval-1.",
        citations: [],
        metadata: { intent: "reserve_stock" },
        created_at: "2026-05-29T18:01:00.000Z",
      },
      run: {
        id: "run-approval",
        agent_type: "ops",
        model: "deterministic-fallback",
        status: "completed",
        intent: "reserve_stock",
        message_text: "Reservá 3 unidades del SKU LAB-RES-900 para LAB-2026-000145",
        response_text: "Prepare la operacion de stock, pero requiere aprobacion humana antes de ejecutarse. Approval approval-1.",
        citations: [],
        metadata: {},
        confidence: 0.95,
        needs_human: true,
        prompt_version: "v1",
        created_at: "2026-05-29T18:00:00.000Z",
        updated_at: "2026-05-29T18:01:00.000Z",
        tool_executions: [
          {
            id: "tool-blocked",
            tool_name: "reserve_stock",
            risk_level: "high_risk_write",
            status: "blocked",
            input_payload: { quantity: 3, sku: "LAB-RES-900" },
            output_payload: {
              approval_request_id: "approval-1",
              summary: "Reservar 3 unidades para LAB-2026-000145",
            },
            latency_ms: 6,
            error: "",
            created_at: "2026-05-29T18:01:00.000Z",
          },
        ],
      },
    });
    vi.mocked(aiApi.approvals.approve).mockResolvedValue({
      id: "approval-1",
      workflow_run: "workflow-1",
      workflow_type: "tool_approval",
      workflow_status: "completed",
      workflow_result: {
        tool_name: "reserve_stock",
        tool_result: { reserved: true },
        post_approval_suggestion: {
          kind: "internal_follow_up",
          title: "Confirmar reserva operativa",
          summary: "La reserva ya quedó activa y conviene dejar constancia para el equipo.",
          suggested_prompt:
            "Creá una nota interna confirmando que quedaron reservadas 3 unidades de LAB-RES-900 para LAB-2026-000145.",
          suggested_message:
            "Reserva activa: 3 unidades de LAB-RES-900 para LAB-2026-000145.",
        },
      },
      action_name: "reserve_stock",
      action_payload: {
        order_number: "LAB-2026-000145",
        quantity: 3,
        sku: "LAB-RES-900",
      },
      status: "approved",
      approved_by: "user-1",
      approved_by_email: "admin@bodegalaabeja.com.ar",
      decision_note: "",
      decided_at: "2026-05-29T18:02:00.000Z",
      created_at: "2026-05-29T18:00:00.000Z",
    });

    renderWithProviders(<BackofficeCopilotPage />);

    await user.type(
      screen.getByLabelText(/mensaje/i),
      "Reservá 3 unidades del SKU LAB-RES-900 para LAB-2026-000145",
    );
    await user.click(screen.getByRole("button", { name: /enviar al copilot/i }));

    expect(await screen.findByText(/Aprobar desde Copilot/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Aprobar desde Copilot/i }));

    await waitFor(() => {
      expect(aiApi.approvals.approve).toHaveBeenCalledWith("approval-1");
    });
    expect(await screen.findByText(/Siguiente paso sugerido/i)).toBeInTheDocument();
    expect(screen.getByText(/Confirmar reserva operativa/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Cargar siguiente paso/i }));
    expect(screen.getByLabelText(/mensaje/i)).toHaveValue(
      "Creá una nota interna confirmando que quedaron reservadas 3 unidades de LAB-RES-900 para LAB-2026-000145.",
    );
  });
});
