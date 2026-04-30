import { Link } from "react-router-dom";
import { PageHero } from "../../components/common/PageHero";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";
import { featuredExperiences, visitFaqs, visitPlanningSteps } from "../../lib/siteContent";

export function VisitPage() {
  return (
    <div>
      <PageHero
        eyebrow="Visitas y hospitalidad"
        title="Planifica una visita que se sienta tan cuidada como la etiqueta que te llevas."
        description="La experiencia ahora tiene una pagina dedicada con propuestas, horarios sugeridos, eventos privados y respuestas concretas para quien esta evaluando venir."
        aside={
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
              Informacion clave
            </p>
            <div className="mt-5 space-y-4 text-burgundy-900">
              <p>
                <span className="font-semibold">Ubicacion:</span> San Rafael, Mendoza
              </p>
              <p>
                <span className="font-semibold">Ventana ideal:</span> jueves a sabado, de 11 a 18 h
              </p>
              <p>
                <span className="font-semibold">Formato:</span> parejas, grupos, corporativo y celebraciones privadas
              </p>
            </div>
          </div>
        }
      >
        <Link to="/contacto?tipo=visita">
          <Button>Solicitar una reserva</Button>
        </Link>
        <Link to="/contacto?tipo=evento">
          <Button variant="ghost">Consultar evento privado</Button>
        </Link>
      </PageHero>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-3">
          {featuredExperiences.map((experience) => (
            <article
              key={experience.title}
              className="rounded-[30px] border border-burgundy-100 bg-white p-6 shadow-velvet"
            >
              <h2 className="font-serif text-3xl text-burgundy-950">{experience.title}</h2>
              <p className="mt-4 leading-7 text-burgundy-800">{experience.description}</p>
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
              <Link to="/contacto?tipo=visita" className="mt-6 inline-flex text-sm font-semibold text-burgundy-900">
                {experience.cta}
              </Link>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="grid gap-10 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-[32px] border border-white/70 bg-burgundy-950 p-8 text-cream-50 shadow-velvet">
            <SectionHeading
              eyebrow="Como funciona"
              title="Una experiencia mejor empieza antes de llegar."
              description="Ordenamos la pagina para que una persona pueda entender rapido que hacer, cuando venir y como coordinar sin friccion."
              tone="light"
            />
            <div className="mt-8 space-y-4">
              {visitPlanningSteps.map((step, index) => (
                <div
                  key={step}
                  className="rounded-[24px] border border-white/10 bg-white/5 px-5 py-4"
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
                    Paso {index + 1}
                  </p>
                  <p className="mt-2 leading-7 text-cream-100/80">{step}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
            <SectionHeading
              eyebrow="FAQ de visitas"
              title="Lo que normalmente preguntaria alguien antes de reservar."
            />
            <div className="mt-8 space-y-4">
              {visitFaqs.map((item) => (
                <details
                  key={item.question}
                  className="rounded-[24px] border border-burgundy-100 bg-cream-50 px-5 py-4"
                >
                  <summary className="cursor-pointer list-none text-lg font-semibold text-burgundy-950">
                    {item.question}
                  </summary>
                  <p className="mt-3 leading-7 text-burgundy-800">{item.answer}</p>
                </details>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
