import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { Link, useParams } from "react-router-dom";
import { ordersApi } from "../../api/orders";
import { paymentsApi } from "../../api/payments";
import { Button } from "../../components/ui/Button";
import { applyWineImageFallback, wineImageSrc } from "../../lib/assets";
import { formatARS, formatDate } from "../../lib/utils";
import { useAuthStore } from "../../store/authStore";

export function OrderDetailPage() {
  const { id = "" } = useParams();
  const accessToken = useAuthStore((state) => state.accessToken);
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["order-detail", id],
    queryFn: () => ordersApi.detail(id),
    enabled: Boolean(accessToken && id),
  });

  const payMutation = useMutation({
    mutationFn: async () => {
      const preference = await paymentsApi.createPreference(id);
      const redirectUrl = preference.init_point ?? preference.sandbox_init_point;
      if (!redirectUrl) {
        throw new Error("Mercado Pago no devolvió una URL válida para reintentar el pago.");
      }
      return redirectUrl;
    },
    onSuccess: (redirectUrl) => {
      window.location.assign(redirectUrl);
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => ordersApi.cancel(id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["order-detail", id] }),
        queryClient.invalidateQueries({ queryKey: ["orders-history"] }),
      ]);
    },
  });

  if (!accessToken) {
    return (
      <section className="mx-auto max-w-4xl px-6 py-16">
        <div className="rounded-[32px] border border-burgundy-100 bg-white p-10 shadow-velvet">
          <h1 className="font-serif text-4xl text-burgundy-950">Necesitás iniciar sesión.</h1>
          <p className="mt-4 text-burgundy-800">
            Entrá por checkout para consultar el detalle real de tus pedidos.
          </p>
          <Link to="/checkout" className="mt-8 inline-flex">
            <Button>Ir al checkout</Button>
          </Link>
        </div>
      </section>
    );
  }

  if (isLoading) {
    return <section className="mx-auto max-w-6xl px-6 py-16">Cargando pedido...</section>;
  }

  if (isError || !data) {
    return (
      <section className="mx-auto max-w-4xl px-6 py-16">
        <div className="rounded-[32px] border border-burgundy-100 bg-white p-10 shadow-velvet">
          <h1 className="font-serif text-4xl text-burgundy-950">No encontramos este pedido.</h1>
          <Link to="/pedidos" className="mt-8 inline-flex">
            <Button>Volver al historial</Button>
          </Link>
        </div>
      </section>
    );
  }

  const canRepay = data.status === "pending_payment" || data.status === "payment_failed";
  const canCancel = canRepay;
  const payError =
    payMutation.error instanceof Error
      ? payMutation.error.message
      : (payMutation.error as AxiosError<{ detail?: string }> | null)?.response?.data?.detail;
  const cancelError = (cancelMutation.error as AxiosError<{ detail?: string }> | null)?.response
    ?.data?.detail;

  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
            Pedido
          </p>
          <h1 className="mt-2 font-serif text-5xl text-burgundy-950">{data.order_number}</h1>
          <p className="mt-3 text-burgundy-700">
            {data.status_label} · creado el {formatDate(data.created_at)}
          </p>
        </div>
        <Link to="/pedidos">
          <Button variant="ghost">Volver al historial</Button>
        </Link>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          {data.items.map((item) => (
            <article
              key={item.id}
              className="grid gap-4 rounded-[28px] border border-burgundy-100 bg-white p-5 shadow-velvet sm:grid-cols-[140px_1fr]"
            >
              <img
                src={wineImageSrc(item.primary_image)}
                alt={item.wine_name}
                onError={applyWineImageFallback}
                className="h-36 w-full rounded-[20px] object-cover"
              />
              <div className="flex flex-col justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    SKU {item.wine_sku}
                  </p>
                  <h2 className="mt-2 font-serif text-2xl text-burgundy-950">{item.wine_name}</h2>
                  <p className="mt-2 text-sm text-burgundy-700">{item.quantity} botella(s)</p>
                </div>
                <div className="flex items-center justify-between">
                  <Link to={`/vinos/${item.wine_slug}`} className="text-sm font-semibold text-burgundy-900">
                    Ver ficha
                  </Link>
                  <p className="text-lg font-semibold text-burgundy-950">{formatARS(item.subtotal)}</p>
                </div>
              </div>
            </article>
          ))}
        </div>

        <aside className="space-y-5">
          <div className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Resumen
            </p>
            <div className="mt-5 space-y-3 text-sm text-burgundy-800">
              <div className="flex items-center justify-between">
                <span>Subtotal</span>
                <span>{formatARS(data.subtotal)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>{data.shipping_method_label}</span>
                <span>{formatARS(data.shipping_cost)}</span>
              </div>
              <div className="flex items-center justify-between text-lg font-semibold text-burgundy-950">
                <span>Total</span>
                <span>{formatARS(data.total)}</span>
              </div>
            </div>
            {data.payment ? (
              <div className="mt-6 rounded-[22px] border border-burgundy-100 bg-cream-50 p-4 text-sm text-burgundy-800">
                <p className="font-semibold text-burgundy-950">Pago</p>
                <p className="mt-2">Estado técnico: {data.payment.status}</p>
                {data.payment.payment_method ? (
                  <p className="mt-1">Medio: {data.payment.payment_method}</p>
                ) : null}
              </div>
            ) : null}

            <div className="mt-6 space-y-3">
              {canRepay ? (
                <Button className="w-full" onClick={() => payMutation.mutate()} disabled={payMutation.isPending}>
                  {payMutation.isPending ? "Redirigiendo a Mercado Pago..." : "Pagar pedido"}
                </Button>
              ) : null}
              {canCancel ? (
                <Button
                  variant="ghost"
                  className="w-full"
                  onClick={() => cancelMutation.mutate()}
                  disabled={cancelMutation.isPending}
                >
                  {cancelMutation.isPending ? "Cancelando..." : "Cancelar pedido"}
                </Button>
              ) : null}
            </div>

            {payError ? (
              <p className="mt-4 text-sm text-burgundy-800">{payError}</p>
            ) : null}
            {cancelError ? (
              <p className="mt-4 text-sm text-burgundy-800">{cancelError}</p>
            ) : null}
          </div>

          <div className="rounded-[32px] border border-white/70 bg-burgundy-950 p-6 text-cream-50 shadow-velvet">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-gold-300">
              Entrega
            </p>
            <div className="mt-5 space-y-2 text-sm leading-6 text-cream-100/80">
              <p>{data.shipping_address.recipient_name}</p>
              <p>
                {data.shipping_address.street} {data.shipping_address.number}
                {data.shipping_address.floor_apt ? ` · ${data.shipping_address.floor_apt}` : ""}
              </p>
              <p>
                {data.shipping_address.city}, {data.shipping_address.province}
              </p>
              <p>
                {data.shipping_address.postal_code} · {data.shipping_address.country}
              </p>
              <p>{data.shipping_address.phone}</p>
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
