import { Link } from "react-router-dom";
import { SectionHeading } from "../../components/common/SectionHeading";
import { editorialCards } from "../../lib/siteContent";

export function EditorialSection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-20">
      <div className="mb-10 flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <SectionHeading
          eyebrow="Notas de marca"
          title="Contenido para elegir mejor, regalar con criterio y conocer la bodega."
          description="Notas breves que acompañan la compra con ideas de servicio, maridaje y hospitalidad."
        />
      </div>
      <div className="grid gap-6 lg:grid-cols-3">
        {editorialCards.map((card) => (
          <Link
            key={card.title}
            to={card.href}
            className="group rounded-lg border border-burgundy-100 bg-white p-6 shadow-velvet transition-transform duration-300 hover:-translate-y-1"
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
