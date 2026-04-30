import { Link } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { SectionHeading } from "../../components/common/SectionHeading";
import { featuredExperiences } from "../../lib/siteContent";

export function ExperiencePreviewSection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-20">
      <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
        <SectionHeading
          eyebrow="Plan Your Visit"
          title="Visitas, catas y formatos privados que merecen una pagina propia."
          description="La referencia que analizamos vende la visita como un producto completo. Aca ya dejamos esa capa visible con experiencias, detalles y CTA claros."
        />
        <div className="grid gap-5">
          {featuredExperiences.map((experience) => (
            <article
              key={experience.title}
              className="rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet"
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
                <Link to="/contacto?tipo=visita" className="shrink-0">
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
