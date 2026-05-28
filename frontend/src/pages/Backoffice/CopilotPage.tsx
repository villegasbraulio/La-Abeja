import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "../../api/ai";
import { Button } from "../../components/ui/Button";
import { formatARS, formatDate } from "../../lib/utils";
import type { AIConversationTurn, AIToolExecution } from "../../types/ai";

const fallbackSuggestions = [
  "Mostrame el stock bajo",
  "Decime las ventas de los últimos 30 días",
  "Qué varietales venden más este mes?",
  "Creá una tarea urgente para seguir el pedido LAB-2026-000145 por pago rechazado",
  "Marcá el pedido LAB-2026-000145 como enviado con tracking AND-12345",
  "Mandale un WhatsApp al cliente del pedido LAB-2026-000145 avisando que sale hoy",
];

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
      void queryClient.invalidateQueries({ queryKey: ["ai-leads"] });
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

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || mutation.isPending) {
      return;
    }
    mutation.mutate({ conversation_id: conversationId, message });
  }

  function usePromptSuggestion(prompt: string) {
    setDraft(prompt);
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              AI Support & Operations Agent
            </p>
            <h3 className="mt-3 font-serif text-4xl text-burgundy-950">
              Copilot operativo para pedidos, ventas, tareas, knowledge y coordinación interna.
            </h3>
            <p className="mt-4 max-w-3xl text-burgundy-700">
              Ahora puede guiar consultas internas, consultar métricas y dejar artefactos operativos
              visibles para el equipo sin salir del backoffice.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2 xl:w-[460px]">
            {[
              {
                label: "Tareas abiertas",
                value: overviewQuery.data?.metrics.open_tasks ?? 0,
              },
              {
                label: "Leads nuevos",
                value: overviewQuery.data?.metrics.new_leads ?? 0,
              },
              {
                label: "Approvals pendientes",
                value: overviewQuery.data?.metrics.pending_approvals ?? 0,
              },
              {
                label: "Runs con revisión humana",
                value: overviewQuery.data?.metrics.runs_needing_human ?? 0,
              },
            ].map((card) => (
              <article
                key={card.label}
                className="rounded-[24px] border border-burgundy-100 bg-cream-50 px-5 py-4"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                  {card.label}
                </p>
                <p className="mt-3 font-serif text-4xl text-burgundy-950">{card.value}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
        <div className="mt-8 space-y-4">
          <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5">
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
                  onClick={() => usePromptSuggestion(prompt)}
                  className="rounded-full border border-burgundy-200 bg-white px-4 py-2 text-left text-sm font-semibold text-burgundy-900 transition hover:border-burgundy-400 hover:bg-burgundy-50"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="max-h-[560px] space-y-4 overflow-y-auto pr-2">
            {orderedTurns.length === 0 ? (
              <div className="rounded-[24px] border border-dashed border-burgundy-200 bg-cream-50 p-6 text-burgundy-700">
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
                “Creá una tarea urgente para seguir el pedido LAB-2026-000145 por pago rechazado”
                <br />
                “Marcá el pedido LAB-2026-000145 como enviado con tracking AND-12345”
              </div>
            ) : null}

            {orderedTurns.map((turn) => (
              <article
                key={turn.id}
                className={`rounded-[24px] border p-5 ${
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

          <form onSubmit={handleSubmit} className="space-y-4 rounded-[28px] border border-burgundy-100 bg-cream-50 p-5">
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-900">Mensaje</span>
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                className="min-h-32 rounded-[22px] border border-burgundy-200 bg-white px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                placeholder="Escribí una consulta operativa o comercial..."
              />
            </label>
            <div className="flex flex-wrap items-center gap-4">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Consultando..." : "Enviar al copilot"}
              </Button>
              <Link to="/backoffice/tareas-ai">
                <Button type="button" variant="ghost">
                  Ver tareas AI
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
        <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
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

        <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
            Ultima accion
          </p>
          {blockedExecutions.length > 0 ? (
            <div className="mt-5 rounded-[24px] border border-amber-200 bg-amber-50 p-5 text-sm text-burgundy-900">
              <p className="font-semibold">Hay acciones esperando aprobacion humana.</p>
              <div className="mt-3 space-y-2">
                {blockedExecutions.map((tool) => (
                  <p key={tool.id}>
                    {tool.tool_name} · approval{" "}
                    {String(tool.output_payload["approval_request_id"] ?? "pendiente")}
                  </p>
                ))}
              </div>
              <Link to="/backoffice/approvals-ai" className="mt-4 inline-flex text-sm font-semibold text-burgundy-900">
                Abrir approvals
              </Link>
            </div>
          ) : writeExecutions.length > 0 ? (
            <div className="mt-5 space-y-3">
              {writeExecutions.map((tool) => (
                <article key={tool.id} className="rounded-[20px] border border-burgundy-100 bg-cream-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {tool.status}
                  </p>
                  <p className="mt-2 font-semibold text-burgundy-950">{tool.tool_name}</p>
                  <p className="mt-2 text-sm text-burgundy-700">
                    {String(
                      tool.output_payload["task_id"] ??
                        tool.output_payload["lead_id"] ??
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
              La ultima sesion no dejo writes ni approvals para revisar.
            </p>
          )}
        </section>

        <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
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

        <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Tareas recientes
            </p>
            <Link to="/backoffice/tareas-ai" className="text-sm font-semibold text-burgundy-800">
              Ver todas
            </Link>
          </div>
          <div className="mt-5 space-y-3">
            {overviewQuery.data?.recent_tasks.length ? (
              overviewQuery.data.recent_tasks.map((task) => (
                <article key={task.id} className="rounded-[20px] border border-burgundy-100 bg-cream-50 p-4">
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

        <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Leads recientes
            </p>
            <Link to="/backoffice/leads-ai" className="text-sm font-semibold text-burgundy-800">
              Ver todos
            </Link>
          </div>
          <div className="mt-5 space-y-3">
            {overviewQuery.data?.recent_leads.length ? (
              overviewQuery.data.recent_leads.map((lead) => (
                <article key={lead.id} className="rounded-[20px] border border-burgundy-100 bg-cream-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {lead.status}
                  </p>
                  <p className="mt-2 font-semibold text-burgundy-950">{lead.full_name}</p>
                  <p className="mt-2 text-sm text-burgundy-700">
                    {lead.company || lead.email || "Sin empresa"}
                  </p>
                  {lead.estimated_order_value ? (
                    <p className="mt-2 text-sm font-semibold text-burgundy-900">
                      Ticket estimado {formatARS(lead.estimated_order_value)}
                    </p>
                  ) : null}
                </article>
              ))
            ) : (
              <p className="text-sm text-burgundy-700">Todavía no hay leads creados por el agente.</p>
            )}
          </div>
        </section>

        <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Approvals pendientes
            </p>
            <Link to="/backoffice/approvals-ai" className="text-sm font-semibold text-burgundy-800">
              Abrir cola
            </Link>
          </div>
          <div className="mt-5 space-y-3">
            {overviewQuery.data?.pending_approvals.length ? (
              overviewQuery.data.pending_approvals.map((approval) => (
                <article key={approval.id} className="rounded-[20px] border border-burgundy-100 bg-cream-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                    {approval.workflow_type}
                  </p>
                  <p className="mt-2 font-semibold text-burgundy-950">{approval.action_name}</p>
                  <p className="mt-2 text-sm text-burgundy-700">{formatDate(approval.created_at)}</p>
                </article>
              ))
            ) : (
              <p className="text-sm text-burgundy-700">No hay approvals pendientes ahora mismo.</p>
            )}
          </div>
        </section>

        <section className="rounded-[32px] border border-white/70 bg-burgundy-950 p-6 text-cream-50 shadow-velvet">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-gold-300">
            Alcance operativo
          </p>
          <ul className="mt-5 space-y-3 text-sm text-cream-100/80">
            <li>• consultas sobre knowledge pública e interna</li>
            <li>• lectura de stock y pedidos</li>
            <li>• métricas de ventas por período, varietal y etiqueta</li>
            <li>• borradores de WhatsApp, leads y tareas internas</li>
            <li>• auditoría por run, tool y workflow</li>
          </ul>
        </section>
      </aside>
      </div>
    </div>
  );
}
