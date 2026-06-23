import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";

export function BackofficeDashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["backoffice-dashboard"],
    queryFn: backofficeApi.dashboard,
  });

  return (
    <div className="space-y-8">
      <section className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Resumen operativo
            </p>
            <h3 className="mt-3 font-serif text-4xl text-burgundy-950">
              Una vista rápida de catálogo, stock y tienda.
            </h3>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to="/backoffice/copilot">
              <Button>Ir al Copilot</Button>
            </Link>
            <Link to="/backoffice/pedidos">
              <Button variant="secondary">Ver pedidos</Button>
            </Link>
            <Link to="/backoffice/metricas">
              <Button variant="ghost">Ver métricas</Button>
            </Link>
            <Link to="/backoffice/tareas">
              <Button variant="ghost">Tareas</Button>
            </Link>
            <Link to="/backoffice/reservas-stock">
              <Button variant="ghost">Reservas de stock</Button>
            </Link>
            <Link to="/backoffice/visitas">
              <Button variant="ghost">Visitas</Button>
            </Link>
            <Link to="/backoffice/cancelaciones">
              <Button variant="ghost">Cancelaciones</Button>
            </Link>
            <Link to="/backoffice/vinos">
              <Button variant="ghost">Gestionar vinos</Button>
            </Link>
            <Link to="/backoffice/categorias">
              <Button variant="ghost">Editar categorías</Button>
            </Link>
          </div>
        </div>
      </section>

      {isLoading ? <p className="text-burgundy-700">Cargando resumen...</p> : null}
      {isError ? (
        <div className="rounded-[28px] border border-burgundy-200 bg-white p-6 text-burgundy-900 shadow-velvet">
          No pudimos cargar el dashboard del backoffice.
        </div>
      ) : null}

      {data ? (
        <>
          <section className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Vinos activos", value: data.active_wines },
              { label: "Destacados", value: data.featured_wines },
              { label: "Stock bajo", value: data.low_stock_wines },
              { label: "Pedidos abiertos", value: data.pending_orders },
            ].map((card) => (
              <article
                key={card.label}
                className="rounded-[28px] border border-burgundy-100 bg-white p-6 shadow-velvet"
              >
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                  {card.label}
                </p>
                <p className="mt-4 font-serif text-5xl text-burgundy-950">{card.value}</p>
              </article>
            ))}
          </section>

          <section className="grid gap-6 lg:grid-cols-[1fr_0.95fr]">
            <div className="rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                Inventario sensible
              </p>
              <div className="mt-5 space-y-4">
                {data.low_stock_items.length > 0 ? (
                  data.low_stock_items.map((item) => (
                    <div
                      key={item.id}
                      className="flex flex-col gap-2 rounded-[22px] border border-burgundy-100 bg-cream-50 px-4 py-4 md:flex-row md:items-center md:justify-between"
                    >
                      <div>
                        <p className="font-semibold text-burgundy-950">{item.name}</p>
                        <p className="text-sm text-burgundy-700">
                          {item.stock} botellas · umbral configurado: {item.low_stock_threshold}
                        </p>
                      </div>
                      <Link to="/backoffice/vinos">
                        <Button variant="ghost">Ajustar stock</Button>
                      </Link>
                    </div>
                  ))
                ) : (
                  <p className="text-burgundy-700">No hay etiquetas en zona de stock bajo.</p>
                )}
              </div>
            </div>

            <div className="rounded-[30px] border border-white/70 bg-burgundy-950 p-6 text-cream-50 shadow-velvet">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-300">
                Estado general
              </p>
              <div className="mt-5 space-y-4 text-sm leading-7 text-cream-100/80">
                <p>Total de vinos cargados: {data.total_wines}</p>
                <p>Categorías activas en catálogo: {data.categories}</p>
                <p>Varietales curados: {data.varietals}</p>
                <p>Pedidos registrados hasta ahora: {data.total_orders}</p>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
