import { Link } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { SectionHeading } from "../../components/common/SectionHeading";
import { hospitalityPromises } from "../../lib/siteContent";

export function ConciergeSection() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:py-20">
      <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-stretch">
        <div className="grid gap-5 md:grid-cols-3 lg:grid-cols-1">
          {hospitalityPromises.map((promise) => (
            <article
              key={promise.label}
              className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-velvet"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                {promise.label}
              </p>
              <p className="mt-3 font-serif text-3xl text-burgundy-950">{promise.value}</p>
              <p className="mt-3 leading-7 text-burgundy-800">{promise.description}</p>
            </article>
          ))}
        </div>
        <div className="rounded-lg border border-burgundy-100 bg-white p-8 shadow-velvet">
          <SectionHeading
            eyebrow="Servicio"
            title="Envío, retiro y visita coordinados sin perder el trato de bodega."
            description="La compra fluye mejor cuando la logística, los tiempos y el acompañamiento están visibles desde el primer clic."
          />
          <div className="mt-8 flex flex-wrap gap-4">
            <Link to="/guia-de-compra">
              <Button>Ver guía de compra</Button>
            </Link>
            <Link to="/contacto">
              <Button variant="ghost">Hablar con el equipo</Button>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
