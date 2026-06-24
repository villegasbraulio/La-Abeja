import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { aiApi } from "../../api/ai";
import { Button } from "../../components/ui/Button";
import { formatDate } from "../../lib/utils";

const reservationStatusOptions = [
  { label: "Todas", value: "" },
  { label: "Activas", value: "active" },
  { label: "Liberadas parciales", value: "partially_released" },
  { label: "Liberadas", value: "released" },
  { label: "Canceladas", value: "cancelled" },
] as const;

const reservationStatusLabels: Record<string, string> = {
  active: "Activa",
  partially_released: "Liberación parcial",
  released: "Liberada",
  cancelled: "Cancelada",
};

export function BackofficeStockReservationsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("active");
  const [selectedReservationId, setSelectedReservationId] = useState<string | null>(null);

  const reservationsQuery = useQuery({
    queryKey: ["ai-stock-reservations", statusFilter, search],
    queryFn: () =>
      aiApi.stockReservations.list({
        status: statusFilter || undefined,
        search: search.trim() || undefined,
      }),
  });

  const reservations = useMemo(() => reservationsQuery.data ?? [], [reservationsQuery.data]);
  const selectedReservation = useMemo(
    () => reservations.find((reservation) => reservation.id === selectedReservationId) ?? null,
    [reservations, selectedReservationId],
  );

  useEffect(() => {
    if (reservations.length === 0) {
      setSelectedReservationId(null);
      return;
    }
    if (
      !selectedReservationId ||
      !reservations.some((reservation) => reservation.id === selectedReservationId)
    ) {
      setSelectedReservationId(reservations[0].id);
    }
  }, [reservations, selectedReservationId]);

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
              Reservas de stock
            </p>
            <h1 className="mt-1.5 text-2xl font-semibold text-burgundy-950">Stock reservado</h1>
          </div>
          <Link to="/backoffice/aprobaciones">
            <Button variant="secondary">Abrir aprobaciones</Button>
          </Link>
        </div>
      </section>

      <section className="grid gap-4 rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] lg:grid-cols-[1fr_240px]">
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Buscar por SKU, vino, pedido, cliente o motivo
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300"
            placeholder="LAB-RES..., cliente@example.com, contingencia"
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Estado
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300"
          >
            {reservationStatusOptions.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <section className="space-y-4">
          {reservationsQuery.isLoading ? <p className="text-burgundy-700">Cargando reservas...</p> : null}
          {reservationsQuery.isError ? (
            <div className="rounded-lg border border-burgundy-200 bg-white p-6 text-burgundy-800 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
              No pudimos cargar las reservas de stock por ahora.
            </div>
          ) : null}
          {reservations.map((reservation) => (
            <button
              key={reservation.id}
              type="button"
              onClick={() => setSelectedReservationId(reservation.id)}
              className={`w-full rounded-lg border p-5 text-left shadow-[0_16px_48px_rgba(66,13,21,0.07)] transition ${
                selectedReservationId === reservation.id
                  ? "border-burgundy-900 bg-burgundy-950 text-cream-50"
                  : "border-burgundy-100 bg-white text-burgundy-950"
              }`}
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-current/70">
                    {reservation.wine_sku}
                  </p>
                  <h4 className="mt-2 text-lg font-semibold">{reservation.wine_name}</h4>
                  <p className="mt-2 text-sm text-current/70">
                    {reservation.quantity} reservadas · {reservation.remaining_quantity} pendientes
                  </p>
                </div>
                <div className="text-left text-sm text-current/70 lg:text-right">
                  <p>{reservationStatusLabels[reservation.status] ?? reservation.status}</p>
                  <p className="mt-2">{formatDate(reservation.created_at)}</p>
                </div>
              </div>
            </button>
          ))}
          {!reservationsQuery.isLoading && reservations.length === 0 ? (
            <div className="rounded-lg border border-burgundy-100 bg-white p-6 text-burgundy-800 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
              No encontramos reservas con esos filtros.
            </div>
          ) : null}
        </section>

        <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          {!selectedReservation ? (
            <p className="text-burgundy-700">Seleccioná una reserva para ver el detalle.</p>
          ) : null}
          {selectedReservation ? (
            <div className="space-y-6">
              <div className="border-b border-burgundy-100 pb-6">
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
                  {selectedReservation.wine_sku}
                </p>
                <h3 className="mt-2 text-2xl font-semibold text-burgundy-950">
                  {selectedReservation.wine_name}
                </h3>
                <p className="mt-3 text-sm text-burgundy-700">
                  {selectedReservation.order_number || "Sin pedido"} ·{" "}
                  {selectedReservation.customer_name || selectedReservation.customer_email || "Sin cliente"}
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800">
                  <p className="font-semibold text-burgundy-950">Estado actual</p>
                  <div className="mt-3 space-y-1">
                    <p>Estado: {reservationStatusLabels[selectedReservation.status] ?? selectedReservation.status}</p>
                    <p>Reservadas: {selectedReservation.quantity}</p>
                    <p>Liberadas: {selectedReservation.released_quantity}</p>
                    <p>Pendientes: {selectedReservation.remaining_quantity}</p>
                  </div>
                </div>
                <div className="rounded-lg border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800">
                  <p className="font-semibold text-burgundy-950">Workflow</p>
                  <div className="mt-3 space-y-1">
                    <p>Workflow: {selectedReservation.workflow_type || "sin workflow asociado"}</p>
                    <p>Creada: {formatDate(selectedReservation.created_at)}</p>
                    <p>
                      Ultima liberación:{" "}
                      {selectedReservation.released_at ? formatDate(selectedReservation.released_at) : "sin liberar"}
                    </p>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border border-burgundy-100 bg-white p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Motivo
                </p>
                <p className="mt-3 whitespace-pre-wrap text-burgundy-900">
                  {selectedReservation.reason || "No se registró un motivo adicional."}
                </p>
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
