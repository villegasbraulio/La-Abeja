import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ordersApi } from "../../api/orders";
import { Button } from "../../components/ui/Button";
import { formatARS, formatDate } from "../../lib/utils";
import { useAuthStore } from "../../store/authStore";

export function OrdersPage() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["orders-history"],
    queryFn: ordersApi.list,
    enabled: Boolean(accessToken),
  });

  if (!accessToken || !user) {
    return (
      <section className="mx-auto max-w-4xl px-6 py-16">
        <div className="rounded-lg border border-burgundy-100 bg-white p-10 shadow-velvet">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
            Pedidos
          </p>
          <h1 className="mt-3 font-serif text-3xl text-burgundy-950 sm:text-4xl">
            Iniciá sesión desde checkout para ver tu historial.
          </h1>
          <p className="mt-4 text-burgundy-800">
            En esta fase 1 los pedidos quedan asociados a un cliente autenticado.
          </p>
          <Link to="/checkout" className="mt-8 inline-flex">
            <Button>Ir al checkout</Button>
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-6xl px-6 py-16">
      <div className="mb-10">
        <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
          Mis pedidos
        </p>
        <h1 className="mt-2 font-serif text-3xl text-burgundy-950 sm:text-4xl">
          Historial de compra de {user.first_name}.
        </h1>
      </div>

      {isLoading ? <p className="text-burgundy-700">Cargando pedidos...</p> : null}
      {isError ? (
        <div className="rounded-lg border border-burgundy-200 bg-white p-6 text-burgundy-800 shadow-velvet">
          No pudimos cargar el historial por ahora.
        </div>
      ) : null}

      <div className="space-y-4">
        {(data?.results ?? []).map((order) => (
          <article
            key={order.id}
            className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-velvet"
          >
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                  {order.order_number}
                </p>
                <h2 className="mt-2 font-serif text-3xl text-burgundy-950">
                  {order.status_label}
                </h2>
                <p className="mt-2 text-burgundy-700">
                  {order.items.length} línea(s) · {formatDate(order.created_at)}
                </p>
              </div>
              <div className="flex flex-col items-start gap-3 lg:items-end">
                <p className="text-2xl font-semibold text-burgundy-950">{formatARS(order.total)}</p>
                <Link to={`/pedidos/${order.id}`}>
                  <Button variant="ghost">Ver detalle</Button>
                </Link>
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
