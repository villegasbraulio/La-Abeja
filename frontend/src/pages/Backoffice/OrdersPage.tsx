import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import { applyWineImageFallback, wineImageSrc } from "../../lib/assets";
import { formatARS, formatDate } from "../../lib/utils";

const statusOptions = [
  { label: "Todos", value: "" },
  { label: "Pendiente de pago", value: "pending_payment" },
  { label: "Pago fallido", value: "payment_failed" },
  { label: "Pagado", value: "paid" },
  { label: "Preparando", value: "preparing" },
  { label: "Listo para enviar", value: "ready_to_ship" },
  { label: "En camino", value: "shipped" },
  { label: "Entregado", value: "delivered" },
  { label: "Cancelado", value: "cancelled" },
  { label: "Reembolsado", value: "refunded" },
] as const;

export function BackofficeOrdersPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);

  const ordersQuery = useQuery({
    queryKey: ["backoffice-orders", search, statusFilter],
    queryFn: () =>
      backofficeApi.orders.list({
        search: search.trim() || undefined,
        status: statusFilter || null,
      }),
  });

  const orders = useMemo(() => ordersQuery.data?.results ?? [], [ordersQuery.data?.results]);

  useEffect(() => {
    if (orders.length === 0) {
      setSelectedOrderId(null);
      return;
    }
    if (!selectedOrderId || !orders.some((order) => order.id === selectedOrderId)) {
      setSelectedOrderId(orders[0].id);
    }
  }, [orders, selectedOrderId]);

  const detailQuery = useQuery({
    queryKey: ["backoffice-order-detail", selectedOrderId],
    queryFn: () => backofficeApi.orders.detail(selectedOrderId ?? ""),
    enabled: Boolean(selectedOrderId),
  });

  return (
    <div className="space-y-8">
      <section className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
        <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
          Operación de pedidos
        </p>
        <h3 className="mt-3 font-serif text-4xl text-burgundy-950">
          Revisá ingresos, estado comercial y datos de entrega sin salir del backoffice.
        </h3>
      </section>

      <section className="grid gap-4 rounded-[28px] border border-burgundy-100 bg-white p-5 shadow-velvet lg:grid-cols-[1fr_240px]">
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Buscar por pedido o cliente
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300"
            placeholder="LAB-2026..., mail o nombre"
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Filtrar por estado
          <select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300"
          >
            {statusOptions.map((option) => (
              <option key={option.value || "all"} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </section>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="space-y-4">
          {ordersQuery.isLoading ? <p className="text-burgundy-700">Cargando pedidos...</p> : null}
          {ordersQuery.isError ? (
            <div className="rounded-[24px] border border-burgundy-200 bg-white p-6 text-burgundy-800 shadow-velvet">
              No pudimos cargar la cola de pedidos por ahora.
            </div>
          ) : null}
          {orders.map((order) => (
            <button
              key={order.id}
              type="button"
              onClick={() => setSelectedOrderId(order.id)}
              className={`w-full rounded-[28px] border p-5 text-left shadow-velvet transition ${
                selectedOrderId === order.id
                  ? "border-burgundy-900 bg-burgundy-950 text-cream-50"
                  : "border-burgundy-100 bg-white text-burgundy-950"
              }`}
            >
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-current/70">
                    {order.order_number}
                  </p>
                  <h4 className="mt-2 font-serif text-2xl">{order.customer_name}</h4>
                  <p className="mt-2 text-sm text-current/70">{order.customer_email}</p>
                </div>
                <div className="text-left lg:text-right">
                  <p className="text-lg font-semibold">{formatARS(order.total)}</p>
                  <p className="mt-2 text-sm text-current/70">{order.status_label}</p>
                </div>
              </div>
              <div className="mt-4 flex flex-wrap gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-current/70">
                <span>{order.item_count} botella(s)</span>
                <span>{order.shipping_method_label}</span>
                <span>{formatDate(order.created_at)}</span>
              </div>
            </button>
          ))}
          {!ordersQuery.isLoading && orders.length === 0 ? (
            <div className="rounded-[24px] border border-burgundy-100 bg-white p-6 text-burgundy-800 shadow-velvet">
              No encontramos pedidos con esos filtros.
            </div>
          ) : null}
        </section>

        <section className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
          {!selectedOrderId ? (
            <p className="text-burgundy-700">Seleccioná un pedido para ver el detalle.</p>
          ) : null}
          {detailQuery.isLoading ? <p className="text-burgundy-700">Cargando detalle...</p> : null}
          {detailQuery.isError ? (
            <div className="rounded-[24px] border border-burgundy-200 bg-cream-50 p-5 text-burgundy-800">
              No pudimos cargar el detalle del pedido seleccionado.
            </div>
          ) : null}
          {detailQuery.data ? (
            <div className="space-y-6">
              <div className="flex flex-col gap-4 border-b border-burgundy-100 pb-6 md:flex-row md:items-end md:justify-between">
                <div>
                  <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
                    {detailQuery.data.order_number}
                  </p>
                  <h3 className="mt-2 font-serif text-4xl text-burgundy-950">
                    {detailQuery.data.customer_name}
                  </h3>
                  <p className="mt-3 text-sm text-burgundy-700">
                    {detailQuery.data.status_label} · {detailQuery.data.customer_email}
                  </p>
                </div>
                <Button variant="ghost" className="w-full md:w-auto">
                  {formatARS(detailQuery.data.total)}
                </Button>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800">
                  <p className="font-semibold text-burgundy-950">Entrega</p>
                  <div className="mt-3 space-y-1">
                    <p>{detailQuery.data.shipping_address.recipient_name}</p>
                    <p>
                      {detailQuery.data.shipping_address.street} {detailQuery.data.shipping_address.number}
                    </p>
                    <p>
                      {detailQuery.data.shipping_address.city}, {detailQuery.data.shipping_address.province}
                    </p>
                    <p>{detailQuery.data.shipping_address.phone}</p>
                  </div>
                </div>

                <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 p-5 text-sm text-burgundy-800">
                  <p className="font-semibold text-burgundy-950">Pago</p>
                  {detailQuery.data.payment ? (
                    <div className="mt-3 space-y-1">
                      <p>Estado: {detailQuery.data.payment.status}</p>
                      <p>Detalle: {detailQuery.data.payment.status_detail || "Sin detalle técnico"}</p>
                      <p>Medio: {detailQuery.data.payment.payment_method || "A confirmar"}</p>
                    </div>
                  ) : (
                    <p className="mt-3">Todavía no hay intento de pago generado.</p>
                  )}
                </div>
              </div>

              <div className="space-y-3">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Líneas del pedido
                </p>
                {detailQuery.data.items.map((item) => (
                  <article
                    key={item.id}
                    className="flex flex-col gap-4 rounded-[24px] border border-burgundy-100 bg-white p-4 md:flex-row md:items-center md:justify-between"
                  >
                    <div className="flex items-center gap-4">
                      <img
                        src={wineImageSrc(item.primary_image)}
                        alt={item.wine_name}
                        onError={applyWineImageFallback}
                        className="h-20 w-16 rounded-2xl object-cover"
                      />
                      <div>
                        <p className="font-semibold text-burgundy-950">{item.wine_name}</p>
                        <p className="text-sm text-burgundy-700">SKU {item.wine_sku}</p>
                      </div>
                    </div>
                    <div className="text-sm text-burgundy-800 md:text-right">
                      <p>{item.quantity} botella(s)</p>
                      <p className="mt-1 font-semibold text-burgundy-950">{formatARS(item.subtotal)}</p>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
