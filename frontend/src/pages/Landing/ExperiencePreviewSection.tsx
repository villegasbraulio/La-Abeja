import { Link } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { SectionHeading } from "../../components/common/SectionHeading";
import { featuredExperiences } from "../../lib/siteContent";

export function ExperiencePreviewSection() {
  return (
    <section className="bg-cream-100/70">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[0.88fr_1.12fr] lg:py-20">
        <SectionHeading
          eyebrow="Reservas"
          title="Visitas pensadas para decidir con el paladar."
          description="Recorridos, catas y propuestas privadas para turistas que quieren conocer la historia, probar etiquetas y comprar mejor."
        />
        <div className="grid gap-5">
          {featuredExperiences.map((experience) => (
            <article
              key={experience.title}
              className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-velvet sm:p-6"
            >
              <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <h3 className="font-serif text-3xl text-burgundy-950">{experience.title}</h3>
                  <p className="mt-3 max-w-2xl leading-7 text-burgundy-800">
                    {experience.description}
                  </p>
                  <div className="mt-5 flex flex-wrap gap-2">
                    {experience.details.map((detail) => (
                      <span
                        key={detail}
                        className="rounded-full bg-burgundy-50 px-3 py-2 text-sm font-medium text-burgundy-800"
                      >
                        {detail}
                      </span>
                    ))}
                  </div>
                </div>
                <Link to="/visitas" className="shrink-0">
                  <Button>{experience.cta}</Button>
                </Link>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
