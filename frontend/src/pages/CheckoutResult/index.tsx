import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ordersApi } from "../../api/orders";
import { Button } from "../../components/ui/Button";
import { formatARS } from "../../lib/utils";
import { useAuthStore } from "../../store/authStore";
import { useCartStore } from "../../store/cartStore";
import { useToastStore } from "../../store/toastStore";

function buildPostPaymentNote(
  status: string,
  shippingMethod: string | undefined,
  hasTracking: boolean,
): string | null {
  if (hasTracking) {
    return null;
  }
  if (!["paid", "preparing", "ready_to_ship"].includes(status)) {
    return null;
  }
  if (shippingMethod === "pickup") {
    return "Recibimos tu pago. Te vamos a escribir por email para coordinar el retiro en bodega.";
  }
  return "Recibimos tu pago. Estamos preparando el pedido y te vamos a enviar por email las novedades del despacho apenas estén disponibles.";
}

function resolveCheckoutStatus(searchParams: URLSearchParams): string | null {
  return (
    searchParams.get("collection_status") ??
    searchParams.get("status") ??
    searchParams.get("payment_status")
  );
}

export function CheckoutResultPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get("order_id");
  const guestAccessToken = searchParams.get("guest_access_token");
  const checkoutStatus = resolveCheckoutStatus(searchParams);
  const paymentId = searchParams.get("payment_id") ?? searchParams.get("collection_id");
  const merchantOrderId = searchParams.get("merchant_order_id");
  const preferenceId = searchParams.get("preference_id");
  const externalReference = searchParams.get("external_reference");
  const clearCart = useCartStore((state) => state.clearCart);
  const showToast = useToastStore((state) => state.showToast);
  const handledStatusRef = useRef<string | null>(null);

  const { data } = useQuery({
    queryKey: ["order-detail", orderId, "checkout-result"],
    queryFn: () => ordersApi.detail(orderId ?? "", guestAccessToken),
    enabled: Boolean(orderId && (accessToken || guestAccessToken)),
  });

  useEffect(() => {
    if (!checkoutStatus || handledStatusRef.current === checkoutStatus) {
      return;
    }

    handledStatusRef.current = checkoutStatus;

    if (checkoutStatus === "approved") {
      clearCart();
      showToast({
        variant: "success",
        title: "Pago confirmado",
        description: "Vaciamos el carrito y dejamos el pedido en seguimiento.",
      });
      return;
    }

    if (checkoutStatus === "pending") {
      showToast({
        variant: "info",
        title: "Pago pendiente",
        description: "Mercado Pago todavía no confirmó la operación.",
      });
      return;
    }

    showToast({
      variant: "error",
      title: "Pago no finalizado",
      description: "Podés revisar el pedido y reintentar el cobro cuando quieras.",
    });
  }, [checkoutStatus, clearCart, showToast]);

  const title =
    checkoutStatus === "approved"
      ? "Pago aprobado"
      : checkoutStatus === "pending"
        ? "Pago pendiente"
        : "Pago no finalizado";

  const description =
    checkoutStatus === "approved"
      ? "Recibimos una confirmacion positiva de Mercado Pago. En breve vas a ver el pedido actualizado con su seguimiento."
      : checkoutStatus === "pending"
        ? "La operacion quedo pendiente. Si elegiste un medio offline, segui las instrucciones del comprobante y revisa luego el estado del pedido."
        : "El pago no terminó aprobado. Podés reintentar desde el detalle del pedido.";

  return (
    <section className="mx-auto max-w-5xl px-6 py-16">
      <div className="rounded-lg border border-burgundy-100 bg-white p-10 shadow-velvet">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
          Resultado del checkout
        </p>
        <h1 className="mt-3 font-serif text-3xl text-burgundy-950 sm:text-4xl">{title}</h1>
        <p className="mt-4 max-w-3xl text-burgundy-800">{description}</p>

        {data ? (
          <div className="mt-8 grid gap-4 rounded-lg border border-burgundy-100 bg-cream-50 p-6 md:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-burgundy-500">Pedido</p>
              <p className="mt-2 text-lg font-semibold text-burgundy-950">{data.order_number}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-burgundy-500">Estado</p>
              <p className="mt-2 text-lg font-semibold text-burgundy-950">{data.status_label}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.16em] text-burgundy-500">Total</p>
              <p className="mt-2 text-lg font-semibold text-burgundy-950">{formatARS(data.total)}</p>
            </div>
          </div>
        ) : null}

        {data ? (
          <div className="mt-6">
            {buildPostPaymentNote(
              data.status,
              data.shipping_method,
              Boolean(data.tracking_number),
            ) ? (
              <div className="rounded-lg border border-burgundy-100 bg-white p-6 text-sm text-burgundy-800">
                <p className="font-semibold text-burgundy-950">Próximo paso</p>
                <p className="mt-2">
                  {buildPostPaymentNote(
                    data.status,
                    data.shipping_method,
                    Boolean(data.tracking_number),
                  )}
                </p>
              </div>
            ) : null}
          </div>
        ) : null}

        {paymentId || merchantOrderId || preferenceId || externalReference ? (
          <div className="mt-6 grid gap-4 rounded-lg border border-burgundy-100 bg-cream-50 p-6 md:grid-cols-2">
            {paymentId ? (
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-burgundy-500">
                  Payment ID
                </p>
                <p className="mt-2 break-all text-sm font-semibold text-burgundy-950">
                  {paymentId}
                </p>
              </div>
            ) : null}
            {merchantOrderId ? (
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-burgundy-500">
                  Merchant Order ID
                </p>
                <p className="mt-2 break-all text-sm font-semibold text-burgundy-950">
                  {merchantOrderId}
                </p>
              </div>
            ) : null}
            {preferenceId ? (
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-burgundy-500">
                  Preference ID
                </p>
                <p className="mt-2 break-all text-sm font-semibold text-burgundy-950">
                  {preferenceId}
                </p>
              </div>
            ) : null}
            {externalReference ? (
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-burgundy-500">
                  Referencia externa
                </p>
                <p className="mt-2 break-all text-sm font-semibold text-burgundy-950">
                  {externalReference}
                </p>
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="mt-8 flex flex-wrap gap-3">
          {orderId ? (
            <Link
              to={
                guestAccessToken
                  ? `/pedidos/${orderId}?guest_access_token=${encodeURIComponent(guestAccessToken)}`
                  : `/pedidos/${orderId}`
              }
            >
              <Button>Ver detalle del pedido</Button>
            </Link>
          ) : null}
          <Link to="/pedidos">
            <Button variant="ghost">Ir a mis pedidos</Button>
          </Link>
          <Link to="/vinos">
            <Button variant="secondary">Volver al catálogo</Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
