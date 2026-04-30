import { Link } from "react-router-dom";
import { SectionHeading } from "../../components/common/SectionHeading";
import { editorialCards } from "../../lib/siteContent";

export function EditorialSection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-20">
      <div className="mb-10 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <SectionHeading
          eyebrow="Notas de marca"
          title="Mas contenido editorial para sostener deseo, contexto y autoridad."
          description="La referencia trabaja muy bien la mezcla entre ecommerce y relato. Estas piezas acercan tu sitio a esa sensacion."
        />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        {editorialCards.map((card) => (
          <Link
            key={card.title}
            to={card.href}
            className="group rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet transition-transform hover:-translate-y-1"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
              {card.eyebrow}
            </p>
            <h3 className="mt-4 font-serif text-3xl text-burgundy-950">{card.title}</h3>
            <p className="mt-4 leading-7 text-burgundy-800">{card.description}</p>
            <p className="mt-6 text-sm font-semibold text-burgundy-900">Seguir leyendo</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
