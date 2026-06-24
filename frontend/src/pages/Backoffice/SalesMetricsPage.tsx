import { useMemo, useState } from "react";
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

const channelLabels: Record<string, string> = {
  web: "Tienda online",
  whatsapp: "WhatsApp",
  email: "Email",
  backoffice: "Venta asistida",
  unknown: "Sin identificar",
};

type BarItem = {
  label: string;
  value: number;
  detail: string;
};

function BarList({ items }: { items: BarItem[] }) {
  const maximum = Math.max(...items.map((item) => item.value), 1);

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

export function BackofficeSalesMetricsPage() {
  const [period, setPeriod] = useState("last_30_days");
  const metricsQuery = useQuery({
    queryKey: ["sales-metrics", period],
    queryFn: () => backofficeApi.salesMetrics(period),
  });
  const data = metricsQuery.data;

  const varietalBars = useMemo<BarItem[]>(
    () =>
      data?.by_varietal.results.map((row) => ({
        label: row.varietal,
        value: row.bottles_sold,
        detail: `${row.bottles_sold} botellas · ${formatARS(row.revenue)}`,
      })) ?? [],
    [data],
  );
  const productBars = useMemo<BarItem[]>(
    () =>
      data?.by_product.results.map((row) => ({
        label: row.wine_name,
        value: Number(row.revenue),
        detail: `${row.bottles_sold} botellas · ${formatARS(row.revenue)}`,
      })) ?? [],
    [data],
  );
  const maxTimelineRevenue = Math.max(
    ...(data?.timeline.results.map((row) => Number(row.total_revenue)) ?? [1]),
    1,
  );

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
              Rendimiento comercial
            </p>
            <h1 className="mt-1.5 text-2xl font-semibold text-burgundy-950">Métricas</h1>
          </div>
          <label className="grid min-w-64 gap-2 text-sm font-semibold text-burgundy-900">
            Período analizado
            <select
              value={period}
              onChange={(event) => setPeriod(event.target.value)}
              className="rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 outline-none focus:border-burgundy-300"
            >
              {periodOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </section>

      {metricsQuery.isLoading ? <p className="text-burgundy-700">Calculando métricas...</p> : null}
      {metricsQuery.isError ? (
        <div className="rounded-lg border border-burgundy-200 bg-white p-6 text-burgundy-900 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          No pudimos calcular las métricas para este período.
        </div>
      ) : null}

      {data ? (
        <>
          <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Facturación", value: formatARS(data.summary.total_revenue) },
              { label: "Pedidos vendidos", value: data.summary.order_count.toLocaleString("es-AR") },
              { label: "Ticket promedio", value: formatARS(data.summary.average_order_value) },
              { label: "Botellas vendidas", value: data.summary.bottles_sold.toLocaleString("es-AR") },
            ].map((card) => (
              <article
                key={card.label}
                className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)]"
              >
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                  {card.label}
                </p>
                <p className="mt-3 text-3xl font-semibold text-burgundy-950">{card.value}</p>
              </article>
            ))}
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
                {formatDate(data.summary.start_at)} — {formatDate(data.summary.end_at)}
              </p>
            </div>
            <div className="mt-8 flex min-h-72 items-end gap-2 overflow-x-auto border-b border-burgundy-100 pb-2">
              {data.timeline.results.map((row) => (
                <div key={row.period} className="flex min-w-14 flex-1 flex-col items-center justify-end gap-2">
                  <span className="text-xs font-semibold text-burgundy-700">
                    {formatARS(row.total_revenue)}
                  </span>
                  <div
                    className="w-full max-w-20 rounded-t-2xl bg-gradient-to-t from-burgundy-950 to-gold-400"
                    style={{
                      height: `${Math.max(14, (Number(row.total_revenue) / maxTimelineRevenue) * 210)}px`,
                    }}
                    title={`${row.order_count} pedidos · ${row.bottles_sold} botellas`}
                  />
                  <span className="whitespace-nowrap text-[11px] text-burgundy-600">
                    {new Intl.DateTimeFormat("es-AR", { day: "2-digit", month: "short" }).format(
                      new Date(row.period),
                    )}
                  </span>
                </div>
              ))}
              {data.timeline.results.length === 0 ? (
                <p className="m-auto text-burgundy-700">No hubo ventas en este período.</p>
              ) : null}
            </div>
          </section>

          <section className="grid gap-6 xl:grid-cols-2">
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
              <h4 className="mt-2 text-xl font-semibold text-burgundy-950">Facturación por etiqueta</h4>
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
                  <p className="text-4xl font-serif"><Percentage value={data.funnel.cart_to_order_rate} /></p>
                  <p className="mt-1 text-sm text-cream-100/70">carrito a pedido</p>
                </div>
                <div>
                  <p className="text-4xl font-serif"><Percentage value={data.funnel.order_to_paid_rate} /></p>
                  <p className="mt-1 text-sm text-cream-100/70">pedido a pago</p>
                </div>
                <p className="border-t border-white/10 pt-4 text-sm text-cream-100/75">
                  {data.funnel.rejected_payment_count} pagos rechazados · {data.funnel.cart_count} carritos
                </p>
              </div>
            </article>

            <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                Clientes
              </p>
              <p className="mt-5 text-4xl font-semibold text-burgundy-950">
                <Percentage value={data.repeat_customers.repeat_rate} />
              </p>
              <p className="mt-2 text-sm text-burgundy-700">tasa de recompra</p>
              <div className="mt-6 space-y-2 text-sm text-burgundy-800">
                <p>{data.repeat_customers.unique_customers} clientes únicos</p>
                <p>{data.repeat_customers.repeat_customers} clientes recurrentes</p>
                <p>{formatARS(data.repeat_customers.average_revenue_per_customer)} por cliente</p>
              </div>
            </article>

            <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                Incidencias
              </p>
              <p className="mt-5 text-4xl font-semibold text-burgundy-950">
                <Percentage value={data.incidents.incident_rate} />
              </p>
              <p className="mt-2 text-sm text-burgundy-700">tasa de incidencias</p>
              <div className="mt-6 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-2xl bg-cream-50 p-3">{data.incidents.refunded_orders} reembolsos</div>
                <div className="rounded-2xl bg-cream-50 p-3">{data.incidents.cancelled_orders} cancelados</div>
                <div className="rounded-2xl bg-cream-50 p-3">{data.incidents.payment_failed_orders} pagos fallidos</div>
                <div className="rounded-2xl bg-cream-50 p-3">{data.incidents.incident_task_count} casos abiertos</div>
              </div>
            </article>
          </section>

          <section className="grid gap-6 xl:grid-cols-2">
            <article className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                Canales de venta
              </p>
              <BarList
                items={data.by_channel.results.map((row) => ({
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
                    <tr><th className="pb-3">Producto</th><th className="pb-3">Ventas</th><th className="pb-3 text-right">Margen</th></tr>
                  </thead>
                  <tbody className="divide-y divide-burgundy-100">
                    {data.margins.results.map((row) => (
                      <tr key={row.sku}>
                        <td className="py-4 pr-3 font-semibold text-burgundy-950">{row.wine_name}</td>
                        <td className="py-4 pr-3 text-burgundy-700">{formatARS(row.revenue)}</td>
                        <td className="py-4 text-right font-semibold text-emerald-700">{formatARS(row.estimated_margin)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          </section>
        </>
      ) : null}
    </div>
  );
}
