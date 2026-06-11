import { Link } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { useCart } from "../../hooks/useCart";
import { applyWineImageFallback, wineImageSrc } from "../../lib/assets";
import { formatARS } from "../../lib/utils";

export function CartPage() {
  const { items, subtotalFormatted, removeItem, updateQuantity, clearCart } = useCart();

  if (items.length === 0) {
    return (
      <section className="mx-auto max-w-5xl px-6 py-16">
        <div className="rounded-[32px] border border-burgundy-100 bg-white p-10 text-center shadow-velvet">
          <p className="text-sm font-semibold uppercase tracking-[0.28em] text-burgundy-500">
            Carrito
          </p>
          <h1 className="mt-3 font-serif text-5xl text-burgundy-950">
            Todavia no agregaste vinos.
          </h1>
          <p className="mt-4 text-burgundy-800">
            Cuando sumes una etiqueta al carrito, la vas a ver aca con cantidad y subtotal.
          </p>
          <Link to="/vinos" className="mt-8 inline-flex">
            <Button>Ir al catalogo</Button>
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-burgundy-600">
            Carrito
          </p>
          <h1 className="mt-2 font-serif text-5xl text-burgundy-950">Tu seleccion</h1>
        </div>
        <Button variant="ghost" onClick={clearCart}>
          Vaciar carrito
        </Button>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          {items.map((item) => (
            <article
              key={item.wineId}
              className="grid gap-4 rounded-[28px] border border-burgundy-100 bg-white p-5 shadow-velvet sm:grid-cols-[140px_1fr]"
            >
              <img
                src={wineImageSrc(item.primaryImage)}
                alt={item.name}
                onError={applyWineImageFallback}
                className="h-36 w-full rounded-[20px] object-cover"
              />
              <div className="flex flex-col justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                    {item.varietalName} · {item.vintageYear}
                  </p>
                  <h2 className="mt-2 font-serif text-2xl text-burgundy-950">{item.name}</h2>
                  <p className="mt-2 text-lg font-semibold text-burgundy-900">
                    {formatARS(item.price)}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <div className="inline-flex items-center rounded-full border border-burgundy-200">
                    <button
                      type="button"
                      className="px-4 py-2 text-burgundy-900"
                      onClick={() => updateQuantity(item.wineId, item.quantity - 1)}
                    >
                      -
                    </button>
                    <span className="px-3 py-2 text-sm font-semibold text-burgundy-900">
                      {item.quantity}
                    </span>
                    <button
                      type="button"
                      className="px-4 py-2 text-burgundy-900"
                      onClick={() => updateQuantity(item.wineId, item.quantity + 1)}
                    >
                      +
                    </button>
                  </div>
                  <button
                    type="button"
                    className="text-sm font-semibold text-burgundy-700"
                    onClick={() => removeItem(item.wineId)}
                  >
                    Quitar
                  </button>
                  <Link
                    to={`/vinos/${item.slug}`}
                    className="text-sm font-semibold text-burgundy-900"
                  >
                    Ver ficha
                  </Link>
                </div>
              </div>
            </article>
          ))}
        </div>

        <div className="space-y-5">
          <aside className="h-fit rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Resumen
            </p>
            <div className="mt-6 flex items-center justify-between">
              <span className="text-burgundy-800">Subtotal</span>
              <span className="text-2xl font-bold text-burgundy-950">{subtotalFormatted}</span>
            </div>
            <p className="mt-4 text-sm leading-6 text-burgundy-700">
              El checkout fase 1 ya crea órdenes reales en backend y deriva el pago a Mercado Pago
              con Checkout Pro.
            </p>
            <div className="mt-6 space-y-3">
              <Link to="/checkout" className="block">
                <Button className="w-full">Continuar compra</Button>
              </Link>
              <Link to="/vinos" className="block">
                <Button variant="ghost" className="w-full">
                  Seguir explorando vinos
                </Button>
              </Link>
            </div>
          </aside>

          <aside className="rounded-[32px] border border-white/70 bg-burgundy-950 p-6 text-cream-50 shadow-velvet">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-gold-300">
              Servicio
            </p>
            <div className="mt-5 space-y-4 text-sm leading-6 text-cream-100/80">
              <p>Retiro en bodega disponible con coordinacion.</p>
              <p>Asistencia para regalos, empresas y eventos privados.</p>
              <p>Guia de compra, FAQ y contacto visibles para reducir friccion.</p>
            </div>
            <div className="mt-6 flex flex-col gap-3">
              <Link to="/guia-de-compra">
                <Button variant="secondary" className="w-full">
                  Ver guia de compra
                </Button>
              </Link>
              <Link to="/contacto?tipo=regalos">
                <Button
                  variant="ghost"
                  className="w-full border-white/30 text-cream-50 hover:bg-white/10"
                >
                  Consultar un regalo
                </Button>
              </Link>
            </div>
          </aside>
        </div>
      </div>
    </section>
  );
}
