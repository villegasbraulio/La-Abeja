import { Link } from "react-router-dom";
import { footerGroups } from "../../lib/siteContent";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-burgundy-100 bg-burgundy-950 text-cream-50">
      <div className="mx-auto grid max-w-7xl gap-10 px-6 py-14 lg:grid-cols-[1.1fr_0.9fr_0.9fr_1fr]">
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
                  className="block text-sm text-cream-100/80 transition-colors hover:text-white"
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
    </footer>
  );
}
