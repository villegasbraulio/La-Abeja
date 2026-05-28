import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "../../api/ai";
import { Button } from "../../components/ui/Button";
import { formatARS, formatDate } from "../../lib/utils";

const leadStatusOptions = [
  { label: "Todos", value: "" },
  { label: "Nuevos", value: "new" },
  { label: "Calificados", value: "qualified" },
  { label: "Contactados", value: "contacted" },
  { label: "Convertidos", value: "converted" },
  { label: "Perdidos", value: "lost" },
] as const;

const leadStatusLabels: Record<string, string> = {
  new: "Nuevo",
  qualified: "Calificado",
  contacted: "Contactado",
  converted: "Convertido",
  lost: "Perdido",
};

export function BackofficeLeadsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("new");
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const leadsQuery = useQuery({
    queryKey: ["ai-leads", statusFilter, search],
    queryFn: () =>
      aiApi.leads.list({
        status: statusFilter || undefined,
        search: search.trim() || undefined,
      }),
  });

  const leads = useMemo(() => leadsQuery.data ?? [], [leadsQuery.data]);
  const selectedLead = useMemo(
    () => leads.find((lead) => lead.id === selectedLeadId) ?? null,
    [leads, selectedLeadId],
  );

  useEffect(() => {
    if (leads.length === 0) {
      setSelectedLeadId(null);
      return;
    }
    if (!selectedLeadId || !leads.some((lead) => lead.id === selectedLeadId)) {
      setSelectedLeadId(leads[0].id);
    }
  }, [leads, selectedLeadId]);

  const updateLeadMutation = useMutation({
    mutationFn: ({ leadId, status }: { leadId: string; status: string }) =>
      aiApi.leads.update(leadId, { status }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["ai-leads"] });
      void queryClient.invalidateQueries({ queryKey: ["ai-copilot-overview"] });
    },
  });

  function updateSelectedLeadStatus(nextStatus: string) {
    if (!selectedLeadId) {
      return;
    }
    updateLeadMutation.mutate({ leadId: selectedLeadId, status: nextStatus });
  }

  return (
    <div className="space-y-8">
      <section className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
          Leads AI
        </p>
        <h3 className="mt-3 font-serif text-4xl text-burgundy-950">
          Oportunidades comerciales detectadas por el agente para regalos, eventos y venta directa.
        </h3>
      </section>

      <section className="grid gap-4 rounded-[28px] border border-burgundy-100 bg-white p-5 shadow-velvet lg:grid-cols-[1fr_240px]">
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Buscar por nombre, mail o empresa
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300"
            placeholder="Lucía, empresa, mail"
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Estado
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300"
          >
            {leadStatusOptions.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <section className="space-y-4">
          {leadsQuery.isLoading ? <p className="text-burgundy-700">Cargando leads AI...</p> : null}
          {leadsQuery.isError ? (
            <div className="rounded-[24px] border border-burgundy-200 bg-white p-6 text-burgundy-800 shadow-velvet">
              No pudimos cargar los leads del agente por ahora.
            </div>
          ) : null}
          {leads.map((lead) => (
            <button
              key={lead.id}
              type="button"
              onClick={() => setSelectedLeadId(lead.id)}
              className={`w-full rounded-[28px] border p-5 text-left shadow-velvet transition ${
                selectedLeadId === lead.id
                  ? "border-burgundy-900 bg-burgundy-950 text-cream-50"
                  : "border-burgundy-100 bg-white text-burgundy-950"
              }`}
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-current/70">
                    {leadStatusLabels[lead.status] ?? lead.status}
                  </p>
                  <h4 className="mt-2 font-serif text-2xl">{lead.full_name}</h4>
                  <p className="mt-2 text-sm text-current/70">{lead.email || "Sin email"} · {lead.company || "Sin empresa"}</p>
                </div>
                <div className="text-left text-sm text-current/70 lg:text-right">
                  <p>{lead.source_channel}</p>
                  <p className="mt-2">{formatDate(lead.created_at)}</p>
                </div>
              </div>
            </button>
          ))}
          {!leadsQuery.isLoading && leads.length === 0 ? (
            <div className="rounded-[24px] border border-burgundy-100 bg-white p-6 text-burgundy-800 shadow-velvet">
              No encontramos leads con esos filtros.
            </div>
          ) : null}
        </section>

        <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
          {!selectedLead ? <p className="text-burgundy-700">Seleccioná un lead para ver el detalle.</p> : null}
          {selectedLead ? (
            <div className="space-y-6">
              <div className="border-b border-burgundy-100 pb-6">
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
                  {leadStatusLabels[selectedLead.status] ?? selectedLead.status}
                </p>
                <h3 className="mt-2 font-serif text-4xl text-burgundy-950">{selectedLead.full_name}</h3>
                <p className="mt-3 text-sm text-burgundy-700">
                  {selectedLead.email || "Sin email"} · {selectedLead.phone || "Sin teléfono"}
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800">
                  <p className="font-semibold text-burgundy-950">Contacto</p>
                  <div className="mt-3 space-y-1">
                    <p>Empresa: {selectedLead.company || "No informada"}</p>
                    <p>Canal: {selectedLead.source_channel}</p>
                    <p>Cliente vinculado: {selectedLead.customer_name || selectedLead.customer_email || "No vinculado"}</p>
                  </div>
                </div>
                <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800">
                  <p className="font-semibold text-burgundy-950">Potencial comercial</p>
                  <div className="mt-3 space-y-1">
                    <p>Creado: {formatDate(selectedLead.created_at)}</p>
                    <p>
                      Ticket estimado:{" "}
                      {selectedLead.estimated_order_value
                        ? formatARS(selectedLead.estimated_order_value)
                        : "Sin estimación"}
                    </p>
                    <p>
                      Varietales:{" "}
                      {selectedLead.desired_varietals.length > 0
                        ? selectedLead.desired_varietals.join(", ")
                        : "Sin preferencia"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-[24px] border border-burgundy-100 bg-white p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Interés detectado
                </p>
                <p className="mt-3 whitespace-pre-wrap text-burgundy-900">
                  {selectedLead.interest_summary || "No hay resumen adicional cargado."}
                </p>
              </div>

              <div className="flex flex-wrap gap-3">
                <Button
                  onClick={() => updateSelectedLeadStatus("qualified")}
                  disabled={updateLeadMutation.isPending}
                >
                  Calificar
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => updateSelectedLeadStatus("contacted")}
                  disabled={updateLeadMutation.isPending}
                >
                  Marcar como contactado
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => updateSelectedLeadStatus("converted")}
                  disabled={updateLeadMutation.isPending}
                >
                  Marcar como convertido
                </Button>
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
