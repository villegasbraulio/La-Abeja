import { useState } from "react";
import { Link } from "react-router-dom";
import { cn } from "../../lib/utils";
import { footerGroups } from "../../lib/siteContent";

export function Footer() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <footer className="mt-16 border-t border-burgundy-100 bg-burgundy-950 text-cream-50">
      <div className="mx-auto max-w-7xl px-6">
        <button
          type="button"
          onClick={() => setIsExpanded((current) => !current)}
          aria-expanded={isExpanded}
          aria-controls="site-footer-content"
          className="flex w-full items-center justify-between gap-6 py-6 text-left transition-colors duration-300 hover:text-gold-200"
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold-300/80">
              Pie del sitio
            </p>
            <p className="mt-2 font-serif text-2xl text-gold-300 md:text-3xl">Bodega La Abeja</p>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-cream-100/75">
              Informacion institucional, navegacion y soporte comercial a un click, sin dejar el
              footer siempre desplegado.
            </p>
          </div>
          <span className="inline-flex items-center gap-3 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-cream-50">
            {isExpanded ? "Cerrar" : "Abrir"}
            <span
              className={cn(
                "inline-flex h-9 w-9 items-center justify-center rounded-full bg-gold-300 text-burgundy-950 transition-transform duration-500",
                isExpanded && "rotate-180",
              )}
            >
              <svg
                aria-hidden="true"
                viewBox="0 0 20 20"
                className="h-4 w-4"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
              >
                <path d="M5 7.5 10 12.5 15 7.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
          </span>
        </button>
      </div>

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
          <div className="mx-auto grid max-w-7xl gap-10 px-6 pb-14 pt-6 lg:grid-cols-[1.1fr_0.9fr_0.9fr_1fr]">
            <div className="max-w-md">
              <p className="font-serif text-3xl text-gold-300">Bodega La Abeja</p>
              <p className="mt-4 leading-7 text-cream-100/80">
                Una bodega de San Rafael reinterpretada como experiencia digital premium: vinos,
                hospitalidad, regalos y automatizaciones visibles en una misma plataforma.
              </p>
              <div className="mt-6 space-y-2 text-sm text-cream-100/75">
                <p>Av. Hipolito Yrigoyen 9500 · San Rafael · Mendoza</p>
                <p>Lunes a sabado · 10 a 18 h · Concierge comercial y de visitas</p>
                <p>Solo para mayores de 18 anos.</p>
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
                Senales de confianza
              </p>
              <div className="mt-5 space-y-3 text-sm text-cream-100/80">
                <p>Envios coordinados, retiro en bodega y soporte humano para compras complejas.</p>
                <p>Asistencia para regalos, eventos privados y selecciones a medida.</p>
                <p>Roadmap listo para checkout, pagos y automatizaciones post compra reales.</p>
              </div>
            </div>
          </div>

          <div className="border-t border-white/10">
            <div className="mx-auto flex max-w-7xl flex-col gap-3 px-6 py-5 text-xs uppercase tracking-[0.18em] text-cream-100/60 md:flex-row md:items-center md:justify-between">
              <p>Portfolio premium para e-commerce vitivinicola y automatizaciones.</p>
              <p>Disenado para mostrar conversion, hospitalidad y experiencia de marca.</p>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
