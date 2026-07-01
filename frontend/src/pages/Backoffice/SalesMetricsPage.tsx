import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { backofficeApi } from "../../api/backoffice";
import { formatARS, formatDate } from "../../lib/utils";

const periodOptions = [
  { value: "last_7_days", label: "Últimos 7 días" },
  { value: "last_30_days", label: "Últimos 30 días" },
  { value: "current_month", label: "Mes actual" },
  { value: "previous_month", label: "Mes anterior" },
  { value: "current_year", label: "Año actual" },
  { value: "last_12_months", label: "Últimos 12 meses" },
] as const;

const metricTabs = [
  { id: "vinos", label: "Vinos", detail: "Botellas, margen y canales" },
  { id: "reservas", label: "Reservas", detail: "Visitas, ocupación y operación" },
] as const;

const channelLabels: Record<string, string> = {
  web: "Tienda online",
  whatsapp: "WhatsApp",
  email: "Email",
  backoffice: "Venta asistida",
  unknown: "Sin identificar",
};

type MetricTab = (typeof metricTabs)[number]["id"];

type BarItem = {
  label: string;
  value: number;
  detail: string;
};

function BarList({ items, emptyLabel = "Sin datos para este período." }: { items: BarItem[]; emptyLabel?: string }) {
  const maximum = Math.max(...items.map((item) => item.value), 1);

  if (items.length === 0) {
    return <p className="mt-6 text-sm text-burgundy-700">{emptyLabel}</p>;
  }

  return (
    <div className="mt-6 space-y-5">
      {items.map((item) => (
        <div key={item.label}>
          <div className="mb-2 flex items-center justify-between gap-4 text-sm">
            <span className="font-semibold text-burgundy-950">{item.label}</span>
            <span className="text-burgundy-700">{item.detail}</span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-burgundy-50">
            <div
              className="h-full rounded-full bg-gradient-to-r from-burgundy-900 to-gold-400"
              style={{ width: `${Math.max(4, (item.value / maximum) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function Percentage({ value }: { value: number }) {
  return <>{new Intl.NumberFormat("es-AR", { style: "percent" }).format(value)}</>;
}

function MetricCard({ label, value, note }: { label: string; value: ReactNode; note?: string }) {
  return (
    <article className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-burgundy-950">{value}</p>
      {note ? <p className="mt-2 text-sm text-burgundy-700">{note}</p> : null}
    </article>
  );
}

function formatPeriodDate(value: string) {
  return new Intl.DateTimeFormat("es-AR", { day: "2-digit", month: "short" }).format(
    new Date(value),
  );
}

export function BackofficeSalesMetricsPage() {
  const [period, setPeriod] = useState("last_30_days");
  const [activeTab, setActiveTab] = useState<MetricTab>("vinos");
  const salesQuery = useQuery({
    queryKey: ["sales-metrics", period],
    queryFn: () => backofficeApi.salesMetrics(period),
    enabled: activeTab === "vinos",
  });
  const reservationQuery = useQuery({
    queryKey: ["reservation-metrics", period],
    queryFn: () => backofficeApi.reservationMetrics(period),
    enabled: activeTab === "reservas",
  });
  const salesData = salesQuery.data;
  const reservationData = reservationQuery.data;

  const varietalBars = useMemo<BarItem[]>(
    () =>
      salesData?.by_varietal.results.map((row) => ({
        label: row.varietal,
        value: row.bottles_sold,
        detail: `${row.bottles_sold} botellas · ${formatARS(row.revenue)}`,
      })) ?? [],
    [salesData],
  );
  const productBars = useMemo<BarItem[]>(
    () =>
      salesData?.by_product.results.map((row) => ({
        label: row.wine_name,
        value: Number(row.revenue),
        detail: `${row.bottles_sold} botellas · ${formatARS(row.revenue)}`,
      })) ?? [],
    [salesData],
  );
  const experienceBars = useMemo<BarItem[]>(
    () =>
      reservationData?.by_experience.results.map((row) => ({
        label: row.experience_name,
        value: Number(row.total_revenue),
        detail: `${row.guest_count} visitantes · ${formatARS(row.total_revenue)}`,
      })) ?? [],
    [reservationData],
  );
  const maxSalesTimelineRevenue = Math.max(
    ...(salesData?.timeline.results.map((row) => Number(row.total_revenue)) ?? [1]),
    1,
  );
  const maxReservationTimelineRevenue = Math.max(
    ...(reservationData?.timeline.results.map((row) => Number(row.total_revenue)) ?? [1]),
    1,
  );

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
              Rendimiento comercial
            </p>
            <h1 className="mt-1.5 text-2xl font-semibold text-burgundy-950">Métricas</h1>
          </div>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
            <div className="grid gap-2">
              <p className="text-sm font-semibold text-burgundy-900">Área analizada</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {metricTabs.map((tab) => (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`rounded-lg border px-4 py-3 text-left transition ${
                      activeTab === tab.id
                        ? "border-burgundy-900 bg-burgundy-950 text-cream-50 shadow-[0_12px_28px_rgba(66,13,21,0.16)]"
                        : "border-burgundy-100 bg-cream-50 text-burgundy-900 hover:border-burgundy-200"
                    }`}
                  >
                    <span className="block text-sm font-semibold">{tab.label}</span>
                    <span
                      className={`mt-1 block text-xs ${
                        activeTab === tab.id ? "text-cream-100/70" : "text-burgundy-600"
                      }`}
                    >
                      {tab.detail}
                    </span>
                  </button>
                ))}
              </div>
            </div>
            <label className="grid min-w-64 gap-2 text-sm font-semibold text-burgundy-900">
              Período analizado
              <select
                value={period}
                onChange={(event) => setPeriod(event.target.value)}
                className="rounded-lg border border-burgundy-100 bg-cream-50 px-4 py-3 outline-none focus:border-burgundy-300"
              >
                {periodOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>
      </section>

      {activeTab === "vinos" ? (
        <>
          {salesQuery.isLoading ? <p className="text-burgundy-700">Calculando métricas...</p> : null}
          {salesQuery.isError ? (
            <div className="rounded-lg border border-burgundy-200 bg-white p-6 text-burgundy-900 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
              No pudimos calcular las métricas de vinos para este período.
            </div>
          ) : null}
          {salesData ? (
            <>
              <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard label="Facturación" value={formatARS(salesData.summary.total_revenue)} />
                <MetricCard
                  label="Pedidos vendidos"
                  value={salesData.summary.order_count.toLocaleString("es-AR")}
                />
                <MetricCard
                  label="Ticket promedio"
                  value={formatARS(salesData.summary.average_order_value)}
                />
                <MetricCard
                  label="Botellas vendidas"
                  value={salesData.summary.bottles_sold.toLocaleString("es-AR")}
                />
              </section>

              <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                <div className="flex flex-wrap items-end justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                      Evolución
                    </p>
                    <h4 className="mt-2 text-xl font-semibold text-burgundy-950">Ventas por período</h4>
                  </div>
                  <p className="text-sm text-burgundy-600">
                    {formatDate(salesData.summary.start_at)} - {formatDate(salesData.summary.end_at)}
                  </p>
                </div>
                <div className="mt-8 flex min-h-72 items-end gap-2 overflow-x-auto border-b border-burgundy-100 pb-2">
                  {salesData.timeline.results.map((row) => (
                    <div
                      key={row.period}
                      className="flex min-w-14 flex-1 flex-col items-center justify-end gap-2"
                    >
                      <span className="text-xs font-semibold text-burgundy-700">
                        {formatARS(row.total_revenue)}
                      </span>
                      <div
                        className="w-full max-w-20 rounded-t-2xl bg-gradient-to-t from-burgundy-950 to-gold-400"
                        style={{
                          height: `${Math.max(
                            14,
                            (Number(row.total_revenue) / maxSalesTimelineRevenue) * 210,
                          )}px`,
                        }}
                        title={`${row.order_count} pedidos · ${row.bottles_sold} botellas`}
                      />
                      <span className="whitespace-nowrap text-[11px] text-burgundy-600">
                        {formatPeriodDate(row.period)}
                      </span>
                    </div>
                  ))}
                  {salesData.timeline.results.length === 0 ? (
                    <p className="m-auto text-burgundy-700">No hubo ventas en este período.</p>
                  ) : null}
                </div>
              </section>

              <section className="space-y-6">
                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Mix varietal
                  </p>
                  <h4 className="mt-2 text-xl font-semibold text-burgundy-950">Botellas por varietal</h4>
                  <BarList items={varietalBars} />
                </article>
                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Productos destacados
                  </p>
                  <h4 className="mt-2 text-xl font-semibold text-burgundy-950">
                    Facturación por etiqueta
                  </h4>
                  <BarList items={productBars} />
                </article>
              </section>

              <section className="grid gap-6 xl:grid-cols-3">
                <article className="rounded-lg border border-burgundy-100 bg-burgundy-950 p-6 text-cream-50 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-300">
                    Conversión
                  </p>
                  <div className="mt-6 space-y-4">
                    <div>
                      <p className="text-4xl font-serif">
                        <Percentage value={salesData.funnel.cart_to_order_rate} />
                      </p>
                      <p className="mt-1 text-sm text-cream-100/70">carrito a pedido</p>
                    </div>
                    <div>
                      <p className="text-4xl font-serif">
                        <Percentage value={salesData.funnel.order_to_paid_rate} />
                      </p>
                      <p className="mt-1 text-sm text-cream-100/70">pedido a pago</p>
                    </div>
                    <p className="border-t border-white/10 pt-4 text-sm text-cream-100/75">
                      {salesData.funnel.rejected_payment_count} pagos rechazados ·{" "}
                      {salesData.funnel.cart_count} carritos
                    </p>
                  </div>
                </article>

                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Clientes
                  </p>
                  <p className="mt-5 text-4xl font-semibold text-burgundy-950">
                    <Percentage value={salesData.repeat_customers.repeat_rate} />
                  </p>
                  <p className="mt-2 text-sm text-burgundy-700">tasa de recompra</p>
                  <div className="mt-6 space-y-2 text-sm text-burgundy-800">
                    <p>{salesData.repeat_customers.unique_customers} clientes únicos</p>
                    <p>{salesData.repeat_customers.repeat_customers} clientes recurrentes</p>
                    <p>{formatARS(salesData.repeat_customers.average_revenue_per_customer)} por cliente</p>
                  </div>
                </article>

                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Incidencias
                  </p>
                  <p className="mt-5 text-4xl font-semibold text-burgundy-950">
                    <Percentage value={salesData.incidents.incident_rate} />
                  </p>
                  <p className="mt-2 text-sm text-burgundy-700">tasa de incidencias</p>
                  <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg bg-cream-50 p-3">{salesData.incidents.refunded_orders} reembolsos</div>
                    <div className="rounded-lg bg-cream-50 p-3">{salesData.incidents.cancelled_orders} cancelados</div>
                    <div className="rounded-lg bg-cream-50 p-3">{salesData.incidents.payment_failed_orders} pagos fallidos</div>
                    <div className="rounded-lg bg-cream-50 p-3">{salesData.incidents.incident_task_count} casos abiertos</div>
                  </div>
                </article>
              </section>

              <section className="space-y-6">
                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Canales de venta
                  </p>
                  <BarList
                    items={salesData.by_channel.results.map((row) => ({
                      label: channelLabels[row.channel] ?? row.channel,
                      value: Number(row.total_revenue),
                      detail: `${row.order_count} pedidos · ${formatARS(row.total_revenue)}`,
                    }))}
                  />
                </article>
                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Margen estimado
                  </p>
                  <div className="mt-6 overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="text-xs uppercase tracking-wider text-burgundy-500">
                        <tr>
                          <th className="pb-3">Producto</th>
                          <th className="pb-3">Ventas</th>
                          <th className="pb-3 text-right">Margen</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-burgundy-100">
                        {salesData.margins.results.map((row) => (
                          <tr key={row.sku}>
                            <td className="py-4 pr-3 font-semibold text-burgundy-950">
                              {row.wine_name}
                            </td>
                            <td className="py-4 pr-3 text-burgundy-700">{formatARS(row.revenue)}</td>
                            <td className="py-4 text-right font-semibold text-emerald-700">
                              {formatARS(row.estimated_margin)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>
              </section>
            </>
          ) : null}
        </>
      ) : null}

      {activeTab === "reservas" ? (
        <>
          {reservationQuery.isLoading ? (
            <p className="text-burgundy-700">Calculando métricas de reservas...</p>
          ) : null}
          {reservationQuery.isError ? (
            <div className="rounded-lg border border-burgundy-200 bg-white p-6 text-burgundy-900 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
              No pudimos calcular las métricas de reservas para este período.
            </div>
          ) : null}
          {reservationData ? (
            <>
              <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
                <MetricCard label="Ingresos por visitas" value={formatARS(reservationData.summary.total_revenue)} />
                <MetricCard
                  label="Reservas cobrables"
                  value={reservationData.summary.revenue_booking_count.toLocaleString("es-AR")}
                  note={`${reservationData.summary.booking_count} reservas totales`}
                />
                <MetricCard
                  label="Visitantes"
                  value={reservationData.summary.total_guests.toLocaleString("es-AR")}
                  note={`${reservationData.summary.average_group_size.toLocaleString("es-AR")} personas por reserva`}
                />
                <MetricCard
                  label="Ocupación"
                  value={<Percentage value={reservationData.capacity.occupancy_rate} />}
                  note={`${reservationData.capacity.booked_guests}/${reservationData.capacity.total_capacity} cupos`}
                />
              </section>

              <section className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                <div className="flex flex-wrap items-end justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                      Demanda de visitas
                    </p>
                    <h4 className="mt-2 text-xl font-semibold text-burgundy-950">
                      Reservas por fecha de visita
                    </h4>
                  </div>
                  <p className="text-sm text-burgundy-600">
                    {formatDate(reservationData.summary.start_at)} - {formatDate(reservationData.summary.end_at)}
                  </p>
                </div>
                <div className="mt-8 flex min-h-72 items-end gap-2 overflow-x-auto border-b border-burgundy-100 pb-2">
                  {reservationData.timeline.results.map((row) => (
                    <div
                      key={row.period}
                      className="flex min-w-14 flex-1 flex-col items-center justify-end gap-2"
                    >
                      <span className="text-xs font-semibold text-burgundy-700">
                        {row.guest_count} pax
                      </span>
                      <div
                        className="w-full max-w-20 rounded-t-2xl bg-gradient-to-t from-burgundy-950 to-gold-400"
                        style={{
                          height: `${Math.max(
                            14,
                            (Number(row.total_revenue) / maxReservationTimelineRevenue) * 210,
                          )}px`,
                        }}
                        title={`${row.booking_count} reservas · ${formatARS(row.total_revenue)}`}
                      />
                      <span className="whitespace-nowrap text-[11px] text-burgundy-600">
                        {formatPeriodDate(row.period)}
                      </span>
                    </div>
                  ))}
                  {reservationData.timeline.results.length === 0 ? (
                    <p className="m-auto text-burgundy-700">No hubo reservas en este período.</p>
                  ) : null}
                </div>
              </section>

              <section className="grid gap-6 xl:grid-cols-3">
                <article className="rounded-lg border border-burgundy-100 bg-burgundy-950 p-6 text-cream-50 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-300">
                    Salud de agenda
                  </p>
                  <div className="mt-6 space-y-5">
                    <div>
                      <p className="text-4xl font-serif">
                        <Percentage value={reservationData.summary.conversion_rate} />
                      </p>
                      <p className="mt-1 text-sm text-cream-100/70">reservas confirmadas o cumplidas</p>
                    </div>
                    <div>
                      <p className="text-4xl font-serif">
                        <Percentage value={reservationData.summary.check_in_rate} />
                      </p>
                      <p className="mt-1 text-sm text-cream-100/70">check-in sobre reservas cobrables</p>
                    </div>
                    <p className="border-t border-white/10 pt-4 text-sm text-cream-100/75">
                      {reservationData.summary.average_lead_days} días promedio entre reserva y visita
                    </p>
                  </div>
                </article>

                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Riesgo operativo
                  </p>
                  <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg bg-cream-50 p-3">
                      <strong className="block text-2xl text-burgundy-950">
                        <Percentage value={reservationData.summary.cancellation_rate} />
                      </strong>
                      cancelaciones
                    </div>
                    <div className="rounded-lg bg-cream-50 p-3">
                      <strong className="block text-2xl text-burgundy-950">
                        <Percentage value={reservationData.summary.no_show_rate} />
                      </strong>
                      no-show
                    </div>
                    <div className="rounded-lg bg-cream-50 p-3">
                      {reservationData.summary.pending_payment_count} pendientes de pago
                    </div>
                    <div className="rounded-lg bg-cream-50 p-3">
                      {reservationData.summary.payment_failed_count} pagos fallidos
                    </div>
                  </div>
                </article>

                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Preparación
                  </p>
                  <div className="mt-6 space-y-3 text-sm text-burgundy-800">
                    <p>{reservationData.operations.special_requests_count} reservas con pedidos especiales</p>
                    <p>{reservationData.operations.dietary_restrictions_count} con restricciones alimentarias</p>
                    <p>{reservationData.operations.pending_refunds_count} reintegros manuales pendientes</p>
                    <p>{reservationData.capacity.blocked_slot_count} turnos bloqueados</p>
                  </div>
                </article>
              </section>

              <section className="space-y-6">
                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Experiencias
                  </p>
                  <h4 className="mt-2 text-xl font-semibold text-burgundy-950">
                    Ingresos y visitantes por experiencia
                  </h4>
                  <BarList items={experienceBars} />
                </article>

                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Estado de reservas
                  </p>
                  <div className="mt-6 overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="text-xs uppercase tracking-wider text-burgundy-500">
                        <tr>
                          <th className="pb-3">Estado</th>
                          <th className="pb-3">Reservas</th>
                          <th className="pb-3">Visitantes</th>
                          <th className="pb-3 text-right">Valor</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-burgundy-100">
                        {reservationData.status_breakdown.results.map((row) => (
                          <tr key={row.status}>
                            <td className="py-4 pr-3 font-semibold text-burgundy-950">{row.label}</td>
                            <td className="py-4 pr-3 text-burgundy-700">{row.booking_count}</td>
                            <td className="py-4 pr-3 text-burgundy-700">{row.guest_count}</td>
                            <td className="py-4 text-right font-semibold text-burgundy-950">
                              {formatARS(row.total_revenue)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </article>

                <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
                  <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    Próximos 14 días
                  </p>
                  <div className="mt-6 overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead className="text-xs uppercase tracking-wider text-burgundy-500">
                        <tr>
                          <th className="pb-3">Fecha</th>
                          <th className="pb-3">Experiencia</th>
                          <th className="pb-3">Hora</th>
                          <th className="pb-3">Cupos</th>
                          <th className="pb-3 text-right">Ocupación</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-burgundy-100">
                        {reservationData.upcoming_slots.map((slot) => (
                          <tr key={slot.slot_id}>
                            <td className="py-4 pr-3 font-semibold text-burgundy-950">
                              {formatDate(slot.date)}
                            </td>
                            <td className="py-4 pr-3 text-burgundy-700">{slot.experience_name}</td>
                            <td className="py-4 pr-3 text-burgundy-700">{slot.start_time}</td>
                            <td className="py-4 pr-3 text-burgundy-700">
                              {slot.booked_guests}/{slot.capacity}
                            </td>
                            <td className="py-4 text-right font-semibold text-burgundy-950">
                              <Percentage value={slot.occupancy_rate} />
                            </td>
                          </tr>
                        ))}
                        {reservationData.upcoming_slots.length === 0 ? (
                          <tr>
                            <td className="py-5 text-burgundy-700" colSpan={5}>
                              No hay turnos abiertos en los próximos 14 días.
                            </td>
                          </tr>
                        ) : null}
                      </tbody>
                    </table>
                  </div>
                </article>
              </section>
            </>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
