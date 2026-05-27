import { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { aiApi } from "../../api/ai";
import { Button } from "../../components/ui/Button";
import { formatDate } from "../../lib/utils";
import type { AIConversationTurn } from "../../types/ai";

export function BackofficeCopilotPage() {
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<AIConversationTurn[]>([]);
  const [lastIntent, setLastIntent] = useState("");
  const [lastModel, setLastModel] = useState("");
  const [lastTools, setLastTools] = useState<string[]>([]);

  const mutation = useMutation({
    mutationFn: aiApi.copilotMessage,
    onSuccess: (data) => {
      setConversationId(data.conversation.id);
      setTurns(data.conversation.turns);
      setLastIntent(data.run.intent);
      setLastModel(data.run.model);
      setLastTools(data.run.tool_executions.map((tool) => tool.tool_name));
      setDraft("");
    },
  });

  const orderedTurns = useMemo(
    () => [...turns].sort((left, right) => left.created_at.localeCompare(right.created_at)),
    [turns],
  );

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || mutation.isPending) {
      return;
    }
    mutation.mutate({ conversation_id: conversationId, message });
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
          AI Support & Operations Agent
        </p>
        <h3 className="mt-3 font-serif text-4xl text-burgundy-950">
          Copilot operativo para consultas internas, stock, pedidos y base de conocimiento.
        </h3>
        <p className="mt-4 max-w-3xl text-burgundy-700">
          Esta primera versión ya puede responder desde knowledge, leer estado vivo con tools y
          auditar cada ejecución dentro del backend.
        </p>

        <div className="mt-8 space-y-4">
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

        <section className="rounded-[32px] border border-white/70 bg-burgundy-950 p-6 text-cream-50 shadow-velvet">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-gold-300">
            Alcance inicial
          </p>
          <ul className="mt-5 space-y-3 text-sm text-cream-100/80">
            <li>• consultas sobre knowledge pública e interna</li>
            <li>• lectura de stock y pedidos</li>
            <li>• auditoría por run y tool</li>
            <li>• base preparada para approvals y workflows</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
