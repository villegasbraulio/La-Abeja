import { ArrowRight, ShoppingBag, X } from "lucide-react";
import { Link } from "react-router-dom";
import { useCart } from "../../hooks/useCart";
import { formatARS } from "../../lib/utils";
import { Button } from "../ui/Button";
import { cn } from "../../lib/utils";

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CartDrawer({ isOpen, onClose }: CartDrawerProps) {
  const { items, itemCount, subtotalFormatted, removeItem } = useCart();
  const previewItems = items.slice(0, 3);
  const hiddenItemsCount = Math.max(items.length - previewItems.length, 0);

  return (
    <div
      className={cn(
        "fixed inset-0 z-[70]",
        isOpen ? "visible pointer-events-auto" : "invisible pointer-events-none",
      )}
      aria-hidden={!isOpen}
    >
      <button
        type="button"
        aria-label="Cerrar carrito"
        onClick={onClose}
        className={cn(
          "absolute inset-0 bg-burgundy-950/35 backdrop-blur-[2px] transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0",
        )}
      />

      <aside
        aria-label="Vista previa del carrito"
        className={cn(
          "absolute right-0 top-0 flex h-full w-full max-w-md flex-col overflow-hidden border-l border-white/10 bg-[linear-gradient(180deg,#4f121f_0%,#2b0e14_100%)] text-cream-50 shadow-[0_32px_90px_-40px_rgba(12,4,6,0.9)] transition-transform duration-500 ease-out",
          isOpen ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="border-b border-white/10 px-6 py-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.24em] text-gold-300/80">
                <ShoppingBag className="h-4 w-4" strokeWidth={1.8} />
                Carrito
              </p>
              <h2 className="mt-3 font-serif text-3xl text-gold-300">
                {itemCount === 0 ? "Tu seleccion esta vacia" : `${itemCount} ${itemCount === 1 ? "vino" : "vinos"} listos`}
              </h2>
              <p className="mt-3 max-w-xs text-sm leading-6 text-cream-100/75">
                Un vistazo rapido antes de pasar al carrito completo o continuar la compra.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Cerrar panel del carrito"
              className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/15 bg-white/5 text-cream-50 transition-colors duration-300 hover:bg-white/10"
            >
              <X className="h-5 w-5" strokeWidth={1.9} />
            </button>
          </div>
        </div>

        {items.length === 0 ? (
          <div className="flex flex-1 flex-col justify-between px-6 py-6">
            <div className="rounded-[28px] border border-white/10 bg-white/5 p-6">
              <p className="text-sm leading-7 text-cream-100/80">
                Agrega algunas etiquetas para ver aca una previa con subtotal, acceso rapido al
                carrito y proximos pasos.
              </p>
            </div>
            <div className="space-y-3">
              <Link to="/vinos" onClick={onClose} className="block">
                <Button variant="secondary" className="w-full">
                  Explorar vinos
                </Button>
              </Link>
              <button
                type="button"
                onClick={onClose}
                className="w-full rounded-full border border-white/20 px-5 py-3 text-sm font-semibold text-cream-50 transition-colors duration-300 hover:bg-white/10"
              >
                Seguir viendo
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="flex-1 space-y-4 overflow-y-auto px-6 py-6">
              {previewItems.map((item) => (
                <article
                  key={item.wineId}
                  className="rounded-[28px] border border-white/10 bg-white/5 p-4"
                >
                  <div className="flex gap-4">
                    <img
                      src={
                        item.primaryImage ??
                        "https://images.unsplash.com/photo-1510812431401-41d2bd2722f3?auto=format&fit=crop&w=900&q=80"
                      }
                      alt={item.name}
                      className="h-24 w-20 rounded-[18px] object-cover"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-gold-300/75">
                        {item.varietalName} · {item.vintageYear}
                      </p>
                      <h3 className="mt-2 font-serif text-xl leading-6 text-white">{item.name}</h3>
                      <div className="mt-4 flex items-center justify-between gap-3">
                        <p className="text-sm text-cream-100/80">
                          {item.quantity} x {formatARS(item.price)}
                        </p>
                        <p className="text-base font-semibold text-gold-300">
                          {formatARS(Number.parseFloat(item.price) * item.quantity)}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeItem(item.wineId)}
                        className="mt-4 text-sm font-semibold text-cream-100/80 transition-colors duration-300 hover:text-white"
                      >
                        Quitar
                      </button>
                    </div>
                  </div>
                </article>
              ))}

              {hiddenItemsCount > 0 ? (
                <div className="rounded-[24px] border border-dashed border-white/15 bg-white/5 px-4 py-4 text-sm text-cream-100/75">
                  Hay {hiddenItemsCount} producto{hiddenItemsCount === 1 ? "" : "s"} mas en el
                  carrito completo.
                </div>
              ) : null}
            </div>

            <div className="border-t border-white/10 bg-black/10 px-6 py-6">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-gold-300/70">
                    Subtotal
                  </p>
                  <p className="mt-2 text-sm text-cream-100/75">
                    Vista previa antes de ir al carrito.
                  </p>
                </div>
                <p className="text-3xl font-semibold text-gold-300">{subtotalFormatted}</p>
              </div>

              <div className="space-y-3">
                <Link to="/carrito" onClick={onClose} className="block">
                  <Button className="w-full justify-between bg-gold-500 text-burgundy-950 hover:bg-gold-400">
                    Ir al carrito
                    <ArrowRight className="h-4 w-4" strokeWidth={1.9} />
                  </Button>
                </Link>
                <Link to="/checkout" onClick={onClose} className="block">
                  <Button
                    variant="ghost"
                    className="w-full justify-between border-white/20 text-cream-50 hover:bg-white/10"
                  >
                    Continuar compra
                    <ArrowRight className="h-4 w-4" strokeWidth={1.9} />
                  </Button>
                </Link>
              </div>
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
