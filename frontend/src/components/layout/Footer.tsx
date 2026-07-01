import { ChevronDown } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { cn } from "../../lib/utils";
import { footerGroups } from "../../lib/siteContent";

export function Footer() {
  const [isExpanded, setIsExpanded] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setIsExpanded(false);
  }, [location.pathname]);

  return (
    <footer className="mt-12 border-t border-burgundy-100 bg-burgundy-950 text-cream-50">
      <div className="mx-auto max-w-7xl px-6">
        <button
          type="button"
          onClick={() => setIsExpanded((current) => !current)}
          aria-expanded={isExpanded}
          aria-controls="site-footer-content"
          className="flex w-full items-center justify-between gap-6 py-5 text-left transition-colors duration-300 hover:text-gold-200"
        >
          <div>
            <p className="mt-2 font-serif text-2xl text-gold-300 md:text-3xl">Bodega La Abeja</p>
          </div>
          <span className="inline-flex items-center gap-3 rounded-lg border border-white/15 bg-white/5 px-3 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-cream-50">
            {isExpanded ? "Cerrar" : "Abrir"}
            <span
              className={cn(
                "inline-flex h-8 w-8 items-center justify-center rounded-md bg-gold-300 text-burgundy-950 transition-transform duration-500",
                isExpanded && "rotate-180",
              )}
            >
              <ChevronDown className="h-4 w-4" strokeWidth={1.8} />
            </span>
          </span>
        </button>
      </div>

      {isExpanded ? (
        <div
          id="site-footer-content"
          className={cn(
            "grid overflow-hidden transition-[grid-template-rows,opacity] duration-500 ease-out",
            isExpanded
              ? "visible grid-rows-[1fr] opacity-100"
              : "invisible grid-rows-[0fr] opacity-0 pointer-events-none",
          )}
        >
          <div className="overflow-hidden">
          <div className="mx-auto grid max-w-7xl gap-8 px-6 pb-12 pt-4 lg:grid-cols-[1.1fr_0.9fr_0.9fr_1fr]">
            <div className="max-w-md">
              <p className="font-serif text-3xl text-gold-300">Bodega La Abeja</p>
              <p className="mt-4 leading-7 text-cream-100/80">
                Vinos de San Rafael, hospitalidad, regalos y visitas en una experiencia de marca
                pensada para comprar con calma y volver.
              </p>
              <div className="mt-6 space-y-2 text-sm text-cream-100/75">
                <p>Av. Hipólito Yrigoyen 9500 · San Rafael · Mendoza</p>
                <p>Lunes a sábado · 10 a 18 h · Concierge comercial y de visitas</p>
                <p>Solo para mayores de 18 años.</p>
              </div>
            </div>

            {footerGroups.map((group) => (
              <div key={group.title}>
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-gold-300">
                  {group.title}
                </p>
                <div className="mt-5 space-y-3">
                  {group.links.map((link) => (
                    <Link
                      key={link.href}
                      to={link.href}
                      className="block text-sm text-cream-100/80 transition-colors duration-300 hover:text-white"
                    >
                      {link.label}
                    </Link>
                  ))}
                </div>
              </div>
            ))}

            <div>
              <p className="text-sm font-semibold uppercase tracking-[0.22em] text-gold-300">
                Señales de confianza
              </p>
              <div className="mt-5 space-y-3 text-sm text-cream-100/80">
                <p>Pago seguro con Mercado Pago, envíos con seguimiento y retiro en bodega.</p>
                <p>Asistencia para regalos, eventos privados y selecciones a medida.</p>
                <Link to="/compra-segura" className="block font-semibold text-gold-300 hover:text-gold-200">
                  Ver políticas de compra segura
                </Link>
              </div>
            </div>
          </div>

          <div className="border-t border-white/10">
            <div className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-5 text-xs uppercase tracking-[0.18em] text-cream-100/60 md:flex-row md:items-center md:justify-between">
              <p>Bodega La Abeja · San Rafael · Mendoza</p>
              <p>Compra online, visitas y regalos con acompañamiento humano.</p>
            </div>
          </div>
          </div>
        </div>
      ) : null}
    </footer>
  );
}
