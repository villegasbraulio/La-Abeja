import { Link } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { SectionHeading } from "../../components/common/SectionHeading";
import { hospitalityPromises } from "../../lib/siteContent";

export function ConciergeSection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-20">
      <div className="grid gap-10 lg:grid-cols-[1fr_0.95fr]">
        <div className="grid gap-5 md:grid-cols-3 lg:grid-cols-1">
          {hospitalityPromises.map((promise) => (
            <article
              key={promise.label}
              className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-velvet"
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
            eyebrow="Concierge"
            title="Envios, retiro, regalos y reservas con acompañamiento del equipo."
            description="Compras personales, regalos corporativos y visitas se coordinan con atención humana de lunes a sábado."
          />
          <div className="mt-8 flex flex-wrap gap-4">
            <Link to="/guia-de-compra">
              <Button>Ver guia de compra</Button>
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
