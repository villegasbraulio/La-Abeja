import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CalendarCheck, CalendarDays, ChartNoAxesColumn, ClipboardList, PackageCheck, ShoppingBag, Wine } from "lucide-react";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";

const quickActions = [
  { label: "Pedidos", href: "/backoffice/pedidos", icon: ShoppingBag, tone: "primary" },
  { label: "Visitas", href: "/backoffice/visitas", icon: CalendarDays, tone: "secondary" },
  { label: "Reservas", href: "/backoffice/reservas", icon: CalendarCheck, tone: "ghost" },
  { label: "Métricas", href: "/backoffice/metricas", icon: ChartNoAxesColumn, tone: "ghost" },
  { label: "Tareas", href: "/backoffice/tareas", icon: ClipboardList, tone: "ghost" },
  { label: "Stock reservado", href: "/backoffice/reservas-stock", icon: PackageCheck, tone: "ghost" },
  { label: "Vinos", href: "/backoffice/vinos", icon: Wine, tone: "ghost" },
] as const;

export function BackofficeDashboardPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["backoffice-dashboard"],
    queryFn: backofficeApi.dashboard,
  });

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
              Consola de escritorio
            </p>
            <h1 className="mt-1.5 text-2xl font-semibold text-burgundy-950">Operación diaria</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-burgundy-700">
              Pedidos, visitas, stock y tareas en una vista pensada para operar desde computadora.
            </p>
          </div>
          <div className="grid gap-2 sm:grid-cols-3 xl:w-[780px]">
            {quickActions.map((action) => {
              const Icon = action.icon;

              return (
                <Link key={action.href} to={action.href}>
                  <Button
                    variant={action.tone}
                    className="w-full justify-start"
                  >
                    <Icon className="h-4 w-4" strokeWidth={1.9} />
                    {action.label}
                  </Button>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {isLoading ? <p className="text-burgundy-700">Cargando resumen...</p> : null}
      {isError ? (
        <div className="rounded-lg border border-burgundy-200 bg-white p-6 text-burgundy-900 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
          No pudimos cargar el dashboard del backoffice.
        </div>
      ) : null}

      {data ? (
        <>
          <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Vinos activos", value: data.active_wines },
              { label: "Destacados", value: data.featured_wines },
              { label: "Stock bajo", value: data.low_stock_wines },
              { label: "Pedidos abiertos", value: data.pending_orders },
            ].map((card) => (
              <article
                key={card.label}
                className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)]"
              >
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                  {card.label}
                </p>
                <p className="mt-3 text-3xl font-semibold text-burgundy-950">{card.value}</p>
              </article>
            ))}
          </section>

          <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
            <div className="flex items-center justify-between gap-4 border-b border-burgundy-100 pb-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Hoy
                </p>
                <h2 className="mt-1.5 text-xl font-semibold text-burgundy-950">
                  Requiere atención
                </h2>
              </div>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {data.action_items.map((item) => (
                <Link
                  key={item.label}
                  to={item.href}
                  className="rounded-lg border border-burgundy-100 bg-cream-50 p-4 transition hover:border-burgundy-300"
                >
                  <p className="text-3xl font-semibold text-burgundy-950">{item.count}</p>
                  <p className="mt-2 text-sm font-semibold text-burgundy-800">{item.label}</p>
                </Link>
              ))}
            </div>
          </section>

          <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
            <div className="flex items-center justify-between gap-4 border-b border-burgundy-100 pb-4">
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Cola de inventario
                </p>
                <h2 className="mt-1.5 text-xl font-semibold text-burgundy-950">
                  Stock bajo y acciones pendientes
                </h2>
              </div>
              <Link to="/backoffice/vinos">
                <Button variant="ghost">
                  <AlertTriangle className="h-4 w-4" strokeWidth={1.9} />
                  Ver catálogo
                </Button>
              </Link>
            </div>

            <div className="mt-5">
                {data.low_stock_items.length > 0 ? (
                  <div className="overflow-hidden rounded-lg border border-burgundy-100">
                    <div className="grid grid-cols-[minmax(240px,1fr)_150px_170px_160px] bg-cream-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
                      <span>Etiqueta</span>
                      <span>Stock</span>
                      <span>Umbral</span>
                      <span className="text-right">Acción</span>
                    </div>
                    {data.low_stock_items.map((item) => (
                      <div
                        key={item.id}
                        className="grid grid-cols-[minmax(240px,1fr)_150px_170px_160px] items-center border-t border-burgundy-100 px-4 py-3 text-sm text-burgundy-800"
                      >
                        <p className="font-semibold text-burgundy-950">{item.name}</p>
                        <p>{item.stock} botellas</p>
                        <p>{item.low_stock_threshold} mínimo</p>
                        <Link to="/backoffice/vinos" className="justify-self-end">
                          <Button variant="ghost" className="min-h-9 px-3 py-1.5">
                            Ajustar
                          </Button>
                        </Link>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-burgundy-700">No hay etiquetas en zona de stock bajo.</p>
                )}
            </div>
          </section>

          <section className="rounded-lg border border-white/70 bg-burgundy-950 p-5 text-cream-50 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-300">
              Estado general
            </p>
            <div className="mt-5 grid gap-4 md:grid-cols-4">
              {[
                ["Total de vinos", data.total_wines],
                ["Categorías activas", data.categories],
                ["Varietales curados", data.varietals],
                ["Pedidos registrados", data.total_orders],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg border border-white/10 bg-white/5 px-4 py-3">
                  <p className="text-xs uppercase tracking-[0.14em] text-cream-100/60">{label}</p>
                  <p className="mt-2 text-2xl font-semibold text-gold-300">{value}</p>
                </div>
              ))}
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
