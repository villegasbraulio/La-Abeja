import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "../../api/ai";
import { Button } from "../../components/ui/Button";
import { formatDate } from "../../lib/utils";
import type { AIApproval, AIConversationTurn, AIToolExecution } from "../../types/ai";

const fallbackSuggestions = [
  "Mostrame el stock bajo",
  "Decime las ventas de los últimos 30 días",
  "Qué varietales venden más este mes?",
  "Buscá pedidos con pago rechazado de los últimos 7 días",
  "Traeme el 360 del cliente ana@example.com",
  "Creá un seguimiento de pago para LAB-2026-000145",
  "Abrí un reclamo logístico para LAB-2026-000145 porque no hay movimiento del tracking",
  "Reservá 3 unidades del SKU LAB-RES-900 para LAB-2026-000145",
  "Pedí cancelación del pedido LAB-2026-000145 por solicitud del cliente",
];

const quickActionCards = [
  {
    title: "Buscar pagos rechazados",
    description: "Encontrá pedidos recientes que necesitan follow-up financiero.",
    prompt: "Buscá pedidos con pago rechazado de los últimos 7 días",
    mode: "send" as const,
  },
  {
    title: "Customer 360",
    description: "Traé pedidos, tareas y notas del cliente para soporte avanzado.",
    prompt: "Traeme el 360 del cliente ana@example.com",
    mode: "draft" as const,
  },
  {
    title: "Seguimiento de pago",
    description: "Prepará una tarea operativa para un pedido con problema de cobro.",
    prompt: "Creá un seguimiento de pago para LAB-2026-000145",
    mode: "draft" as const,
  },
  {
    title: "Reclamo logístico",
    description: "Abrí una incidencia cuando el envío no avanza o falta tracking.",
    prompt: "Abrí un reclamo logístico para LAB-2026-000145 porque no hay movimiento del tracking",
    mode: "draft" as const,
  },
  {
    title: "Reservar stock",
    description: "Prepará una reserva con aprobación para separar unidades críticas.",
    prompt: "Reservá 3 unidades del SKU LAB-RES-900 para LAB-2026-000145",
    mode: "draft" as const,
  },
  {
    title: "Pedir cancelación",
    description: "Dejá lista una cancelación con trazabilidad y aprobación humana.",
    prompt: "Pedí cancelación del pedido LAB-2026-000145 por solicitud del cliente",
    mode: "draft" as const,
  },
  {
    title: "Visitas activas",
    description: "Listá las experiencias de visita publicadas o destacadas.",
    prompt: "Mostrame las visitas activas y destacadas",
    mode: "draft" as const,
  },
  {
    title: "Reservas de visita",
    description: "Buscá reservas, eventos y turnos por cliente o código.",
    prompt: "Buscá reservas de visita del cliente ana@example.com",
    mode: "draft" as const,
  },
  {
    title: "Eventos de esta semana",
    description: "Revisá la agenda operativa de experiencias y cupos.",
    prompt: "Qué eventos y turnos de visita tengo esta semana?",
    mode: "draft" as const,
  },
];

type PostApprovalSuggestion = {
  kind: string;
  title: string;
  summary: string;
  suggested_prompt?: string;
  suggested_message?: string;
};

function getPostApprovalSuggestion(approval: AIApproval | undefined): PostApprovalSuggestion | null {
  const rawSuggestion = approval?.workflow_result?.["post_approval_suggestion"];
  if (!rawSuggestion || typeof rawSuggestion !== "object" || Array.isArray(rawSuggestion)) {
    return null;
  }

  const suggestion = rawSuggestion as Record<string, unknown>;
  if (
    typeof suggestion.title !== "string" ||
    typeof suggestion.summary !== "string" ||
    typeof suggestion.kind !== "string"
  ) {
    return null;
  }

  return {
    kind: suggestion.kind,
    title: suggestion.title,
    summary: suggestion.summary,
    suggested_prompt:
      typeof suggestion.suggested_prompt === "string" ? suggestion.suggested_prompt : undefined,
    suggested_message:
      typeof suggestion.suggested_message === "string" ? suggestion.suggested_message : undefined,
  };
}

export function BackofficeCopilotPage() {
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<AIConversationTurn[]>([]);
  const [lastIntent, setLastIntent] = useState("");
  const [lastModel, setLastModel] = useState("");
  const [lastExecutions, setLastExecutions] = useState<AIToolExecution[]>([]);
  const queryClient = useQueryClient();

  const overviewQuery = useQuery({
    queryKey: ["ai-copilot-overview"],
    queryFn: aiApi.overview,
  });

  const mutation = useMutation({
    mutationFn: aiApi.copilotMessage,
    onSuccess: (data) => {
      setConversationId(data.conversation.id);
      setTurns(data.conversation.turns);
      setLastIntent(data.run.intent);
      setLastModel(data.run.model);
      setLastExecutions(data.run.tool_executions);
      setDraft("");
      void queryClient.invalidateQueries({ queryKey: ["ai-copilot-overview"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-approvals"] });
    },
  });

  const orderedTurns = useMemo(
    () => [...turns].sort((left, right) => left.created_at.localeCompare(right.created_at)),
    [turns],
  );
  const promptSuggestions = overviewQuery.data?.prompt_suggestions ?? fallbackSuggestions;
  const lastTools = useMemo(
    () => [...new Set(lastExecutions.map((tool) => tool.tool_name))],
    [lastExecutions],
  );
  const blockedExecutions = useMemo(
    () => lastExecutions.filter((tool) => tool.status === "blocked"),
    [lastExecutions],
  );
  const writeExecutions = useMemo(
    () => lastExecutions.filter((tool) => tool.risk_level !== "read_only"),
    [lastExecutions],
  );
  const inlineApprovalId = useMemo(() => {
    const latestBlocked = blockedExecutions.at(-1);
    const rawApprovalId = latestBlocked?.output_payload["approval_request_id"];
    return typeof rawApprovalId === "string" ? rawApprovalId : null;
  }, [blockedExecutions]);
  const inlineApprovalSummary = useMemo(() => {
    const latestBlocked = blockedExecutions.at(-1);
    const rawSummary = latestBlocked?.output_payload["summary"];
    return typeof rawSummary === "string" ? rawSummary : "";
  }, [blockedExecutions]);

  const inlineApprovalQuery = useQuery({
    queryKey: ["ai-approval", inlineApprovalId],
    queryFn: () => aiApi.approvals.detail(inlineApprovalId!),
    enabled: Boolean(inlineApprovalId),
  });
  const inlinePostApprovalSuggestion = useMemo(
    () => getPostApprovalSuggestion(inlineApprovalQuery.data),
    [inlineApprovalQuery.data],
  );

  const approvalMutationOptions = {
    onSuccess: (data: AIApproval) => {
      if (inlineApprovalId) {
        queryClient.setQueryData(["ai-approval", inlineApprovalId], data);
      }
      void queryClient.invalidateQueries({ queryKey: ["ai-approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-cancellation-approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-copilot-overview"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-stock-reservations"] });
    },
  };

  const approveInlineMutation = useMutation({
    mutationFn: (approvalId: string) => aiApi.approvals.approve(approvalId),
    ...approvalMutationOptions,
  });

  const rejectInlineMutation = useMutation({
    mutationFn: (approvalId: string) => aiApi.approvals.reject(approvalId),
    ...approvalMutationOptions,
  });

  function submitMessage(message: string) {
    const normalized = message.trim();
    if (!normalized || mutation.isPending) {
      return;
    }
    mutation.mutate({ conversation_id: conversationId, message: normalized });
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    submitMessage(draft);
  }

  function loadPromptSuggestion(prompt: string) {
    setDraft(prompt);
  }

  function handleQuickAction(prompt: string, mode: "draft" | "send") {
    if (mode === "send") {
      setDraft(prompt);
      submitMessage(prompt);
      return;
    }
    loadPromptSuggestion(prompt);
  }

  function handleInlineApprove() {
    if (!inlineApprovalId) {
      return;
    }
    approveInlineMutation.mutate(inlineApprovalId);
  }

  function handleInlineReject() {
    if (!inlineApprovalId) {
      return;
    }
    rejectInlineMutation.mutate(inlineApprovalId);
  }

  function handleLoadPostApprovalSuggestion() {
    if (!inlinePostApprovalSuggestion) {
      return;
    }
    setDraft(
      inlinePostApprovalSuggestion.suggested_prompt ||
        inlinePostApprovalSuggestion.suggested_message ||
        "",
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
              Asistente de soporte y operaciones
            </p>
            <h1 className="mt-1.5 text-2xl font-semibold text-burgundy-950">Copilot operativo</h1>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:w-[560px]">
            {[
              {
                label: "Tareas abiertas",
                value: overviewQuery.data?.metrics.open_tasks ?? 0,
              },
              {
                label: "Aprobaciones pendientes",
                value: overviewQuery.data?.metrics.pending_approvals ?? 0,
              },
              {
                label: "Runs con revisión humana",
                value: overviewQuery.data?.metrics.runs_needing_human ?? 0,
              },
              {
                label: "Reservas activas",
                value: overviewQuery.data?.metrics.active_stock_reservations ?? 0,
              },
              {
                label: "Cancelaciones pendientes",
                value: overviewQuery.data?.metrics.pending_cancellation_approvals ?? 0,
              },
            ].map((card) => (
              <article
                key={card.label}
                className="rounded-lg border border-burgundy-100 bg-cream-50 px-4 py-3"
              >
                <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-burgundy-500">
                  {card.label}
                </p>
                <p className="mt-2 text-2xl font-semibold text-burgundy-950">{card.value}</p>
              </article>
            ))}
          </div>
        </div>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link to="/backoffice/metricas">
            <Button variant="ghost">Métricas</Button>
          </Link>
          <Link to="/backoffice/tareas">
            <Button variant="ghost">Tareas</Button>
          </Link>
          <Link to="/backoffice/aprobaciones">
            <Button variant="ghost">Aprobaciones</Button>
          </Link>
          <Link to="/backoffice/reservas-stock">
            <Button variant="ghost">Reservas de stock</Button>
          </Link>
          <Link to="/backoffice/cancelaciones">
            <Button variant="ghost">Cancelaciones</Button>
          </Link>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
        <div className="mt-8 space-y-4">
          <div className="rounded-lg border border-burgundy-100 bg-white p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Acciones disponibles
                </p>
                <p className="mt-2 text-sm text-burgundy-700">
                  Atajos para pedidos, pagos, logística, reservas y visitas.
                </p>
              </div>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {quickActionCards.map((action) => (
                <article key={action.title} className="rounded-lg border border-burgundy-100 bg-cream-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {action.mode === "send" ? "Ejecuta ahora" : "Usa prompt"}
                  </p>
                  <h4 className="mt-2 font-semibold text-burgundy-950">{action.title}</h4>
                  <p className="mt-2 text-sm text-burgundy-700">{action.description}</p>
                  <button
                    type="button"
                    onClick={() => handleQuickAction(action.prompt, action.mode)}
                    className="mt-4 rounded-full border border-burgundy-200 bg-white px-4 py-2 text-sm font-semibold text-burgundy-900 transition hover:border-burgundy-400 hover:bg-burgundy-50"
                  >
                    {action.mode === "send" ? "Ejecutar" : "Cargar prompt"}
                  </button>
                </article>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-burgundy-100 bg-cream-50 p-5">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Prompts guiados
                </p>
                <p className="mt-2 text-sm text-burgundy-700">
                  Elegí una idea y ajustala antes de enviarla si necesitás más precisión.
                </p>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              {promptSuggestions.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => loadPromptSuggestion(prompt)}
                  className="rounded-full border border-burgundy-200 bg-white px-4 py-2 text-left text-sm font-semibold text-burgundy-900 transition hover:border-burgundy-400 hover:bg-burgundy-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="max-h-[560px] space-y-4 overflow-y-auto pr-2">
            {orderedTurns.length === 0 ? (
              <div className="rounded-lg border border-dashed border-burgundy-200 bg-cream-50 p-6 text-burgundy-700">
                Probá con preguntas como:
                <br />
                “Mostrame el stock bajo”
                <br />
                “Que dice la base sobre retiro en bodega?”
                <br />
                “Que pedidos pendientes tengo hoy?”
                <br />
                “Qué varietales venden más este mes?”
                <br />
                “Traeme el 360 del cliente ana@example.com”
                <br />
                “Reservá 3 unidades del SKU LAB-RES-900 para LAB-2026-000145”
              </div>
            ) : null}

            {orderedTurns.map((turn) => (
              <article
                key={turn.id}
                className={`rounded-lg border p-5 ${
                  turn.role === "assistant"
                    ? "border-burgundy-100 bg-white"
                    : "border-transparent bg-burgundy-950 text-cream-50"
                }`}
              >
                <div className="flex flex-wrap items-center gap-3">
                  <p
                    className={`text-xs font-semibold uppercase tracking-[0.2em] ${
                      turn.role === "assistant" ? "text-burgundy-500" : "text-gold-300"
                    }`}
                  >
                    {turn.role === "assistant" ? "Copilot" : "Operador"}
                  </p>
                  <p
                    className={`text-xs ${
                      turn.role === "assistant" ? "text-burgundy-500/70" : "text-cream-100/70"
                    }`}
                  >
                    {formatDate(turn.created_at)}
                  </p>
                </div>
                <p className="mt-3 whitespace-pre-wrap leading-7">{turn.content}</p>
                {turn.citations.length > 0 ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {turn.citations.map((citation, index) => (
                      <span
                        key={`${citation.document_id ?? "doc"}-${index}`}
                        className="rounded-full bg-burgundy-50 px-3 py-2 text-xs font-semibold text-burgundy-800"
                      >
                        {citation.document_title || "Base de conocimiento"}
                        {citation.section ? ` · ${citation.section}` : ""}
                      </span>
                    ))}
                  </div>
                ) : null}
              </article>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 rounded-lg border border-burgundy-100 bg-cream-50 p-5">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-900">Mensaje</span>
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                className="min-h-32 rounded-lg border border-burgundy-200 bg-white px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                placeholder="Escribí una consulta operativa o comercial..."
              />
            </label>
            <div className="flex flex-wrap items-center gap-4">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Consultando..." : "Enviar al copilot"}
              </Button>
              <Link to="/backoffice/tareas">
                <Button type="button" variant="ghost">
                  Ver tareas
                </Button>
              </Link>
              <Link to="/backoffice/reservas-stock">
                <Button type="button" variant="ghost">
                  Ver reservas de stock
                </Button>
              </Link>
              {mutation.isError ? (
                <p className="text-sm text-burgundy-700">No pudimos consultar el agente por ahora.</p>
              ) : null}
            </div>
          </form>
        </div>
      </section>

      <aside className="space-y-6">
        <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
            Estado actual
          </p>
          <div className="mt-5 space-y-3 text-sm text-burgundy-800">
            <p>
              <span className="font-semibold text-burgundy-950">Conversación:</span>{" "}
              {conversationId ? "activa" : "sin iniciar"}
            </p>
            <p>
              <span className="font-semibold text-burgundy-950">Último intent:</span>{" "}
              {lastIntent || "sin clasificar"}
            </p>
            <p>
              <span className="font-semibold text-burgundy-950">Modelo:</span>{" "}
              {lastModel || "fallback deterministico"}
            </p>
          </div>
        </section>

        <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
            Ultima accion
          </p>
          {blockedExecutions.length > 0 ? (
            <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-5 text-sm text-burgundy-900">
              <p className="font-semibold">Hay acciones esperando aprobacion humana.</p>
              <div className="mt-3 space-y-2">
                {blockedExecutions.map((tool) => (
                  <p key={tool.id}>
                    {tool.tool_name} · aprobación{" "}
                    {String(tool.output_payload["approval_request_id"] ?? "pendiente")}
                  </p>
                ))}
              </div>
              {inlineApprovalSummary ? (
                <p className="mt-4 text-sm text-burgundy-800">{inlineApprovalSummary}</p>
              ) : null}
              {inlineApprovalQuery.data ? (
                <div className="mt-4 rounded-lg border border-amber-200 bg-white p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    Approval inline
                  </p>
                  <p className="mt-2 font-semibold text-burgundy-950">
                    {inlineApprovalQuery.data.action_name}
                  </p>
                  <p className="mt-2 text-sm text-burgundy-700">
                    Estado {inlineApprovalQuery.data.status}
                    {inlineApprovalQuery.data.workflow_status
                      ? ` · workflow ${inlineApprovalQuery.data.workflow_status}`
                      : ""}
                  </p>
                  <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl bg-cream-50 p-3 text-xs text-burgundy-900">
                    {JSON.stringify(inlineApprovalQuery.data.action_payload, null, 2)}
                  </pre>
                  {inlinePostApprovalSuggestion ? (
                    <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
                        Siguiente paso sugerido
                      </p>
                      <p className="mt-2 font-semibold text-burgundy-950">
                        {inlinePostApprovalSuggestion.title}
                      </p>
                      <p className="mt-2 text-sm leading-6 text-burgundy-800">
                        {inlinePostApprovalSuggestion.summary}
                      </p>
                      {inlinePostApprovalSuggestion.suggested_message ? (
                        <div className="mt-3 rounded-2xl bg-white/80 p-3 text-sm text-burgundy-900">
                          {inlinePostApprovalSuggestion.suggested_message}
                        </div>
                      ) : null}
                      {(inlinePostApprovalSuggestion.suggested_prompt ||
                        inlinePostApprovalSuggestion.suggested_message) ? (
                        <div className="mt-4 flex flex-wrap gap-3">
                          <Button type="button" onClick={handleLoadPostApprovalSuggestion}>
                            Cargar siguiente paso
                          </Button>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                  {Object.keys(inlineApprovalQuery.data.workflow_result).length > 0 &&
                  !inlinePostApprovalSuggestion ? (
                    <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl bg-cream-50 p-3 text-xs text-burgundy-900">
                      {JSON.stringify(inlineApprovalQuery.data.workflow_result, null, 2)}
                    </pre>
                  ) : null}
                  {inlineApprovalQuery.data.status === "pending" ? (
                    <div className="mt-4 flex flex-wrap gap-3">
                      <Button
                        type="button"
                        onClick={handleInlineApprove}
                        disabled={approveInlineMutation.isPending || rejectInlineMutation.isPending}
                      >
                        Aprobar desde Copilot
                      </Button>
                      <Button
                        type="button"
                        variant="secondary"
                        onClick={handleInlineReject}
                        disabled={approveInlineMutation.isPending || rejectInlineMutation.isPending}
                      >
                        Rechazar
                      </Button>
                    </div>
                  ) : null}
                </div>
              ) : null}
              <div className="mt-4 flex flex-wrap gap-3">
                <Link to="/backoffice/aprobaciones" className="inline-flex text-sm font-semibold text-burgundy-900">
                  Abrir aprobaciones
                </Link>
                <Link to="/backoffice/cancelaciones" className="inline-flex text-sm font-semibold text-burgundy-900">
                  Ver cancelaciones
                </Link>
              </div>
            </div>
          ) : writeExecutions.length > 0 ? (
            <div className="mt-5 space-y-3">
              {writeExecutions.map((tool) => (
                <article key={tool.id} className="rounded-lg border border-burgundy-100 bg-cream-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {tool.status}
                  </p>
                  <p className="mt-2 font-semibold text-burgundy-950">{tool.tool_name}</p>
                  <p className="mt-2 text-sm text-burgundy-700">
                    {String(
                        tool.output_payload["task_id"] ??
                        tool.output_payload["lead_id"] ??
                        tool.output_payload["reservation_id"] ??
                        tool.output_payload["order_number"] ??
                        tool.output_payload["to"] ??
                        "Accion auditada",
                    )}
                  </p>
                </article>
              ))}
            </div>
          ) : (
            <p className="mt-5 text-sm text-burgundy-700">
              La ultima sesion no dejó acciones ni aprobaciones para revisar.
            </p>
          )}
        </section>

        <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
            Tools usadas
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {lastTools.length > 0 ? (
              lastTools.map((tool) => (
                <span
                  key={tool}
                  className="rounded-full bg-burgundy-50 px-3 py-2 text-xs font-semibold text-burgundy-800"
                >
                  {tool}
                </span>
              ))
            ) : (
              <p className="text-sm text-burgundy-700">Todavía no hubo ejecuciones en esta sesión.</p>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Tareas recientes
            </p>
            <Link to="/backoffice/tareas" className="text-sm font-semibold text-burgundy-800">
              Ver todas
            </Link>
          </div>
          <div className="mt-5 space-y-3">
            {overviewQuery.data?.recent_tasks.length ? (
              overviewQuery.data.recent_tasks.map((task) => (
                <article key={task.id} className="rounded-lg border border-burgundy-100 bg-cream-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {task.task_type}
                  </p>
                  <p className="mt-2 font-semibold text-burgundy-950">{task.title}</p>
                  <p className="mt-2 text-sm text-burgundy-700">
                    {task.order_number || task.customer_email || "Sin referencia"} · {task.status}
                  </p>
                </article>
              ))
            ) : (
              <p className="text-sm text-burgundy-700">Todavía no hay tareas generadas en esta etapa.</p>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Reservas recientes
            </p>
            <Link to="/backoffice/reservas-stock" className="text-sm font-semibold text-burgundy-800">
              Ver todas
            </Link>
          </div>
          <div className="mt-5 space-y-3">
            {overviewQuery.data?.recent_stock_reservations.length ? (
              overviewQuery.data.recent_stock_reservations.map((reservation) => (
                <article key={reservation.id} className="rounded-lg border border-burgundy-100 bg-cream-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {reservation.status}
                  </p>
                  <p className="mt-2 font-semibold text-burgundy-950">{reservation.wine_name}</p>
                  <p className="mt-2 text-sm text-burgundy-700">
                    {reservation.wine_sku} · {reservation.remaining_quantity} pendientes
                  </p>
                </article>
              ))
            ) : (
              <p className="text-sm text-burgundy-700">Todavía no hay reservas de stock creadas por el agente.</p>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Aprobaciones pendientes
            </p>
            <Link to="/backoffice/aprobaciones" className="text-sm font-semibold text-burgundy-800">
              Abrir cola
            </Link>
          </div>
          <div className="mt-5 space-y-3">
            {overviewQuery.data?.pending_approvals.length ? (
              overviewQuery.data.pending_approvals.map((approval) => (
                <article key={approval.id} className="rounded-lg border border-burgundy-100 bg-cream-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {approval.workflow_type}
                  </p>
                  <p className="mt-2 font-semibold text-burgundy-950">{approval.action_name}</p>
                  <p className="mt-2 text-sm text-burgundy-700">{formatDate(approval.created_at)}</p>
                </article>
              ))
            ) : (
              <p className="text-sm text-burgundy-700">No hay aprobaciones pendientes ahora mismo.</p>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Cancelaciones pendientes
            </p>
            <Link to="/backoffice/cancelaciones" className="text-sm font-semibold text-burgundy-800">
              Abrir cola
            </Link>
          </div>
          <div className="mt-5 space-y-3">
            {overviewQuery.data?.pending_cancellation_approvals.length ? (
              overviewQuery.data.pending_cancellation_approvals.map((approval) => (
                <article key={approval.id} className="rounded-lg border border-burgundy-100 bg-cream-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {approval.status}
                  </p>
                  <p className="mt-2 font-semibold text-burgundy-950">
                    {String(approval.action_payload.order_number ?? "Pedido sin referencia")}
                  </p>
                  <p className="mt-2 text-sm text-burgundy-700">{formatDate(approval.created_at)}</p>
                </article>
              ))
            ) : (
              <p className="text-sm text-burgundy-700">No hay cancelaciones esperando decisión ahora mismo.</p>
            )}
          </div>
        </section>

        <section className="rounded-lg border border-white/70 bg-burgundy-950 p-6 text-cream-50 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-gold-300">
            Alcance operativo
          </p>
          <ul className="mt-5 space-y-3 text-sm text-cream-100/80">
            <li>• consultas sobre knowledge pública e interna</li>
            <li>• lectura de stock y pedidos</li>
            <li>• métricas de ventas por período, varietal y etiqueta</li>
            <li>• follow-ups de pago, reclamos logísticos y reservas de stock</li>
            <li>• aprobaciones humanas para acciones sensibles y cancelaciones</li>
            <li>• auditoría por conversación, acción y reserva</li>
          </ul>
        </section>
      </aside>
      </div>
    </div>
  );
}
