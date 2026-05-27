import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ordersApi } from "../../api/orders";
import { Button } from "../../components/ui/Button";
import { formatARS } from "../../lib/utils";
import { useAuthStore } from "../../store/authStore";
import { useCartStore } from "../../store/cartStore";

export function CheckoutResultPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const [searchParams] = useSearchParams();
  const orderId = searchParams.get("order_id");
  const checkoutStatus = searchParams.get("status");
  const clearCart = useCartStore((state) => state.clearCart);

  const { data } = useQuery({
    queryKey: ["order-detail", orderId, "checkout-result"],
    queryFn: () => ordersApi.detail(orderId ?? ""),
    enabled: Boolean(accessToken && orderId),
  });

  useEffect(() => {
    if (checkoutStatus === "approved") {
      clearCart();
    }
  }, [checkoutStatus, clearCart]);

  const title =
    checkoutStatus === "approved"
      ? "Pago aprobado"
      : checkoutStatus === "pending"
        ? "Pago pendiente"
        : "Pago no finalizado";

  const description =
    checkoutStatus === "approved"
      ? "Mercado Pago nos devolvió una confirmación positiva. El webhook del backend termina de consolidar el estado real del pedido."
      : checkoutStatus === "pending"
        ? "La operación quedó pendiente. Vas a poder revisar el estado real desde tu historial de pedidos."
        : "El flujo de pago no terminó aprobado. Podés reintentar desde el detalle del pedido.";

  return (
    <section className="mx-auto max-w-5xl px-6 py-16">
      <div className="rounded-[32px] border border-burgundy-100 bg-white p-10 shadow-velvet">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
          Resultado del checkout
        </p>
        <h1 className="mt-3 font-serif text-5xl text-burgundy-950">{title}</h1>
        <p className="mt-4 max-w-3xl text-burgundy-800">{description}</p>

        {data ? (
          <div className="mt-8 grid gap-4 rounded-[24px] border border-burgundy-100 bg-cream-50 p-6 md:grid-cols-3">
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

        <div className="mt-8 flex flex-wrap gap-3">
          {orderId ? (
            <Link to={`/pedidos/${orderId}`}>
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
