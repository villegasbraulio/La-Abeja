import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "../../api/ai";
import { Button } from "../../components/ui/Button";
import { formatDate } from "../../lib/utils";

const taskStatusOptions = [
  { label: "Todas", value: "" },
  { label: "Abiertas", value: "open" },
  { label: "En progreso", value: "in_progress" },
  { label: "Bloqueadas", value: "blocked" },
  { label: "Completadas", value: "completed" },
] as const;

const taskTypeLabels: Record<string, string> = {
  support_follow_up: "Seguimiento soporte",
  order_issue: "Incidente de pedido",
  order_review: "Revisión manual",
  payment_review: "Revisión de pago",
  lead_follow_up: "Seguimiento comercial",
  conversation_escalation: "Escalación humana",
  restock: "Reposición",
  shipping_claim: "Reclamo logístico",
  cancellation_review: "Revisión de cancelación",
};

const priorityLabels: Record<string, string> = {
  low: "Baja",
  medium: "Media",
  high: "Alta",
  urgent: "Urgente",
};

export function BackofficeTasksPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("open");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const tasksQuery = useQuery({
    queryKey: ["ai-tasks", statusFilter, search],
    queryFn: () =>
      aiApi.tasks.list({
        status: statusFilter || undefined,
        search: search.trim() || undefined,
      }),
  });

  const tasks = useMemo(() => tasksQuery.data ?? [], [tasksQuery.data]);
  const selectedTask = useMemo(
    () => tasks.find((task) => task.id === selectedTaskId) ?? null,
    [tasks, selectedTaskId],
  );

  useEffect(() => {
    if (tasks.length === 0) {
      setSelectedTaskId(null);
      return;
    }
    if (!selectedTaskId || !tasks.some((task) => task.id === selectedTaskId)) {
      setSelectedTaskId(tasks[0].id);
    }
  }, [tasks, selectedTaskId]);

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: string }) =>
      aiApi.tasks.update(taskId, { status }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai-tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-copilot-overview"] });
    },
  });

  function updateSelectedTaskStatus(nextStatus: string) {
    if (!selectedTaskId) {
      return;
    }
    updateTaskMutation.mutate({ taskId: selectedTaskId, status: nextStatus });
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
          Tareas operativas
        </p>
        <h1 className="mt-1.5 text-2xl font-semibold text-burgundy-950">Tareas</h1>
      </section>

      <section className="grid gap-4 rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] lg:grid-cols-[1fr_240px]">
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Buscar por título, pedido o cliente
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300"
            placeholder="demora, LAB-2026..., mail"
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Estado
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300"
          >
            {taskStatusOptions.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className="space-y-6">
        <section className="space-y-4">
          {tasksQuery.isLoading ? <p className="text-burgundy-700">Cargando tareas...</p> : null}
          {tasksQuery.isError ? (
            <div className="rounded-lg border border-burgundy-200 bg-white p-6 text-burgundy-800 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
              No pudimos cargar la cola de tareas por ahora.
            </div>
          ) : null}
          {tasks.map((task) => (
            <button
              key={task.id}
              type="button"
              onClick={() => setSelectedTaskId(task.id)}
              className={`w-full rounded-lg border p-5 text-left shadow-[0_16px_48px_rgba(66,13,21,0.07)] transition ${
                selectedTaskId === task.id
                  ? "border-burgundy-900 bg-burgundy-950 text-cream-50"
                  : "border-burgundy-100 bg-white text-burgundy-950"
              }`}
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-current/70">
                    {taskTypeLabels[task.task_type] ?? task.task_type}
                  </p>
                  <h4 className="mt-2 text-lg font-semibold">{task.title}</h4>
                  <p className="mt-2 text-sm text-current/70">
                    {priorityLabels[task.priority] ?? task.priority} · {task.status}
                  </p>
                </div>
                <div className="text-left text-sm text-current/70 lg:text-right">
                  <p>{task.order_number || "Sin pedido vinculado"}</p>
                  <p className="mt-2">{formatDate(task.created_at)}</p>
                </div>
              </div>
            </button>
          ))}
          {!tasksQuery.isLoading && tasks.length === 0 ? (
            <div className="rounded-lg border border-burgundy-100 bg-white p-6 text-burgundy-800 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
              No encontramos tareas con esos filtros.
            </div>
          ) : null}
        </section>

        <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          {!selectedTask ? <p className="text-burgundy-700">Seleccioná una tarea para ver el detalle.</p> : null}
          {selectedTask ? (
            <div className="space-y-6">
              <div className="border-b border-burgundy-100 pb-6">
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
                  {taskTypeLabels[selectedTask.task_type] ?? selectedTask.task_type}
                </p>
                <h3 className="mt-2 text-2xl font-semibold text-burgundy-950">{selectedTask.title}</h3>
                <p className="mt-3 text-sm text-burgundy-700">
                  {selectedTask.customer_name || selectedTask.customer_email || "Sin cliente"} ·{" "}
                  {selectedTask.order_number || "Sin pedido"}
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800">
                  <p className="font-semibold text-burgundy-950">Estado actual</p>
                  <div className="mt-3 space-y-1">
                    <p>Estado: {selectedTask.status}</p>
                    <p>Prioridad: {priorityLabels[selectedTask.priority] ?? selectedTask.priority}</p>
                    <p>Asignado a: {selectedTask.assigned_to_name || selectedTask.assigned_to_email || "Sin asignar"}</p>
                    <p>Workflow: {selectedTask.workflow_type || "manual"}</p>
                  </div>
                </div>
                <div className="rounded-lg border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800">
                  <p className="font-semibold text-burgundy-950">Timing</p>
                  <div className="mt-3 space-y-1">
                    <p>Creada: {formatDate(selectedTask.created_at)}</p>
                    <p>Actualizada: {formatDate(selectedTask.updated_at)}</p>
                    <p>Vence: {selectedTask.due_at ? formatDate(selectedTask.due_at) : "Sin vencimiento"}</p>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-burgundy-100 bg-white p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Descripción
                </p>
                <p className="mt-3 whitespace-pre-wrap text-burgundy-900">
                  {selectedTask.description || "No hay descripción adicional."}
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Button
                  onClick={() => updateSelectedTaskStatus("in_progress")}
                  disabled={updateTaskMutation.isPending}
                >
                  Pasar a en progreso
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => updateSelectedTaskStatus("completed")}
                  disabled={updateTaskMutation.isPending}
                >
                  Marcar como completada
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => updateSelectedTaskStatus("blocked")}
                  disabled={updateTaskMutation.isPending}
                >
                  Marcar como bloqueada
                </Button>
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
