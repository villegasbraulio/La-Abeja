import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "../../api/ai";
import { Button } from "../../components/ui/Button";
import { formatDate } from "../../lib/utils";

const approvalStatusOptions = [
  { label: "Pendientes", value: "pending" },
  { label: "Aprobados", value: "approved" },
  { label: "Rechazados", value: "rejected" },
] as const;

export function BackofficeApprovalsPage() {
  const [statusFilter, setStatusFilter] = useState("pending");
  const [selectedApprovalId, setSelectedApprovalId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const approvalsQuery = useQuery({
    queryKey: ["ai-approvals", statusFilter],
    queryFn: () =>
      aiApi.approvals.list({
        status: statusFilter || undefined,
      }),
  });

  const approvals = useMemo(() => approvalsQuery.data ?? [], [approvalsQuery.data]);
  const selectedApproval = useMemo(
    () => approvals.find((approval) => approval.id === selectedApprovalId) ?? null,
    [approvals, selectedApprovalId],
  );

  useEffect(() => {
    if (approvals.length === 0) {
      setSelectedApprovalId(null);
      return;
    }
    if (!selectedApprovalId || !approvals.some((approval) => approval.id === selectedApprovalId)) {
      setSelectedApprovalId(approvals[0].id);
    }
  }, [approvals, selectedApprovalId]);

  const approveMutation = useMutation({
    mutationFn: (approvalId: string) => aiApi.approvals.approve(approvalId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai-approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-copilot-overview"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-leads"] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (approvalId: string) => aiApi.approvals.reject(approvalId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai-approvals"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-copilot-overview"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-tasks"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-leads"] });
    },
  });

  function handleApprove() {
    if (!selectedApprovalId) {
      return;
    }
    approveMutation.mutate(selectedApprovalId);
  }

  function handleReject() {
    if (!selectedApprovalId) {
      return;
    }
    rejectMutation.mutate(selectedApprovalId);
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
          Approvals AI
        </p>
        <h3 className="mt-3 font-serif text-4xl text-burgundy-950">
          Cola de decisiones humanas para cualquier workflow que el agente no deba cerrar solo.
        </h3>
      </section>

      <section className="rounded-[28px] border border-burgundy-100 bg-white p-5 shadow-velvet">
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Estado
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300 md:w-72"
          >
            {approvalStatusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="space-y-4">
          {approvalsQuery.isLoading ? <p className="text-burgundy-700">Cargando approvals...</p> : null}
          {approvalsQuery.isError ? (
            <div className="rounded-[24px] border border-burgundy-200 bg-white p-6 text-burgundy-800 shadow-velvet">
              No pudimos cargar la cola de approvals por ahora.
            </div>
          ) : null}
          {approvals.map((approval) => (
            <button
              key={approval.id}
              type="button"
              onClick={() => setSelectedApprovalId(approval.id)}
              className={`w-full rounded-[28px] border p-5 text-left shadow-velvet transition ${
                selectedApprovalId === approval.id
                  ? "border-burgundy-900 bg-burgundy-950 text-cream-50"
                  : "border-burgundy-100 bg-white text-burgundy-950"
              }`}
            >
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-current/70">
                {approval.workflow_type}
              </p>
              <h4 className="mt-2 font-serif text-2xl">{approval.action_name}</h4>
              <div className="mt-3 flex flex-wrap gap-3 text-sm text-current/70">
                <span>{approval.status}</span>
                <span>{formatDate(approval.created_at)}</span>
              </div>
            </button>
          ))}
          {!approvalsQuery.isLoading && approvals.length === 0 ? (
            <div className="rounded-[24px] border border-burgundy-100 bg-white p-6 text-burgundy-800 shadow-velvet">
              No hay approvals para ese estado.
            </div>
          ) : null}
        </section>

        <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
          {!selectedApproval ? (
            <p className="text-burgundy-700">Seleccioná una solicitud para revisar su detalle.</p>
          ) : null}
          {selectedApproval ? (
            <div className="space-y-6">
              <div className="border-b border-burgundy-100 pb-6">
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
                  {selectedApproval.workflow_type}
                </p>
                <h3 className="mt-2 font-serif text-4xl text-burgundy-950">
                  {selectedApproval.action_name}
                </h3>
                <p className="mt-3 text-sm text-burgundy-700">
                  Estado: {selectedApproval.status}
                  {selectedApproval.workflow_status ? ` · workflow ${selectedApproval.workflow_status}` : ""}
                  {selectedApproval.approved_by_email ? ` · decidido por ${selectedApproval.approved_by_email}` : ""}
                </p>
              </div>

              <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Payload de acción
                </p>
                <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl bg-white p-4 text-sm text-burgundy-900">
                  {JSON.stringify(selectedApproval.action_payload, null, 2)}
                </pre>
              </div>

              {Object.keys(selectedApproval.workflow_result).length > 0 ? (
                <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Resultado del workflow
                  </p>
                  <pre className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-2xl bg-white p-4 text-sm text-burgundy-900">
                    {JSON.stringify(selectedApproval.workflow_result, null, 2)}
                  </pre>
                </div>
              ) : null}

              {selectedApproval.decision_note ? (
                <div className="rounded-[24px] border border-burgundy-100 bg-white p-5">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Nota de decisión
                  </p>
                  <p className="mt-3 whitespace-pre-wrap text-burgundy-900">
                    {selectedApproval.decision_note}
                  </p>
                </div>
              ) : null}

              {selectedApproval.status === "pending" ? (
                <div className="flex flex-wrap gap-3">
                  <Button onClick={handleApprove} disabled={approveMutation.isPending || rejectMutation.isPending}>
                    Aprobar y ejecutar
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={handleReject}
                    disabled={approveMutation.isPending || rejectMutation.isPending}
                  >
                    Rechazar
                  </Button>
                </div>
              ) : null}
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
