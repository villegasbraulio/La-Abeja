import { Link } from "react-router-dom";
import { PageHero } from "../../components/common/PageHero";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";
import { guideFaqs, shippingHighlights } from "../../lib/siteContent";

export function GuidePage() {
  return (
    <div>
      <PageHero
        eyebrow="Guia de compra y envios"
        title="Todo lo necesario para comprar con tranquilidad."
        description="Envios, retiro en bodega, preguntas frecuentes y criterios de atencion para resolver dudas antes de confirmar el pedido."
        aside={
          <div className="space-y-4 text-burgundy-900">
            <p>
              <span className="font-semibold">Cobertura:</span> Cuyo y AMBA priorizados
            </p>
            <p>
              <span className="font-semibold">Retiro:</span> disponible con coordinacion previa
            </p>
            <p>
              <span className="font-semibold">Asistencia:</span> soporte humano para regalos, volumen y visitas
            </p>
          </div>
        }
      >
        <Link to="/contacto?tipo=envios">
          <Button>Consultar un envio</Button>
        </Link>
        <Link to="/carrito">
          <Button variant="ghost">Ver carrito</Button>
        </Link>
      </PageHero>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-6 md:grid-cols-3">
          {shippingHighlights.map((highlight) => (
            <article
              key={highlight.title}
              className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-[0_16px_48px_rgba(66,13,21,0.08)]"
            >
              <h2 className="font-serif text-2xl text-burgundy-950">{highlight.title}</h2>
              <p className="mt-4 leading-7 text-burgundy-800">{highlight.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="retiro" className="mx-auto max-w-7xl px-6 py-20">
        <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="rounded-lg border border-burgundy-100 bg-white p-8 shadow-[0_16px_48px_rgba(66,13,21,0.08)]">
            <SectionHeading
              eyebrow="Retiro en bodega"
              title="Una opcion simple y visible para quienes pasan por San Rafael."
            />
            <p className="mt-6 leading-8 text-burgundy-800">
              Comprar online y retirar en bodega permite sumar flexibilidad, evitar esperas y
              aprovechar la visita para descubrir nuevas etiquetas con el equipo.
            </p>
          </div>
          <div className="rounded-lg border border-white/70 bg-burgundy-950 p-8 text-cream-50 shadow-[0_16px_48px_rgba(66,13,21,0.08)]">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-300">
              Lo que comunica
            </p>
            <ul className="mt-6 list-disc space-y-3 pl-5 text-cream-100/80">
              <li>Coordinacion posterior a la compra con franja horaria sugerida.</li>
              <li>Oportunidad de sumar visita, regalo o compra asistida el mismo dia.</li>
              <li>Menos friccion para clientes locales o turistas con agenda ajustada.</li>
            </ul>
          </div>
        </div>
      </section>

      <section id="faq" className="mx-auto max-w-7xl px-6 py-8">
        <div className="rounded-lg border border-burgundy-100 bg-white px-6 py-8 shadow-[0_16px_48px_rgba(66,13,21,0.08)] md:px-8">
          <SectionHeading
            eyebrow="FAQ"
            title="Preguntas frecuentes"
          />
          <div className="mt-6 space-y-3">
            {guideFaqs.map((item) => (
              <details
                key={item.question}
                className="rounded-lg border border-burgundy-100 bg-cream-50 px-5 py-4"
              >
                <summary className="cursor-pointer list-none text-base font-semibold text-burgundy-950">
                  {item.question}
                </summary>
                <p className="mt-3 leading-7 text-burgundy-800">{item.answer}</p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
