import { Link } from "react-router-dom";
import { PageHero } from "../../components/common/PageHero";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";
import { aboutPillars, storyMilestones } from "../../lib/siteContent";

export function AboutPage() {
  return (
    <div>
      <PageHero
        eyebrow="Historia y marca"
        title="La bodega se cuenta desde el legado, el terroir y la hospitalidad."
        description="La coleccion nace de una historia concreta: viñas, cava, recepcion y una forma mendocina de recibir que sigue guiando la experiencia."
        aside={
          <img
            src="https://images.unsplash.com/photo-1506377247377-2a5b3b417ebb?auto=format&fit=crop&w=1200&q=80"
            alt="Barricas y cava de la bodega"
            className="h-[320px] w-full rounded-lg object-cover"
          />
        }
      >
        <Link to="/visitas">
          <Button>Vivir la bodega</Button>
        </Link>
        <Link to="/vinos">
          <Button variant="ghost">Explorar la coleccion</Button>
        </Link>
      </PageHero>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-6 md:grid-cols-3">
          {aboutPillars.map((pillar) => (
            <article
              key={pillar.title}
              className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-velvet"
            >
              <h2 className="font-serif text-3xl text-burgundy-950">{pillar.title}</h2>
              <p className="mt-4 leading-7 text-burgundy-800">{pillar.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="rounded-lg border border-burgundy-100 bg-white px-8 py-10 shadow-velvet md:px-10">
          <SectionHeading
            eyebrow="Linea de tiempo"
            title="Una cronologia breve para entender como se fue formando la identidad de la bodega."
          />
          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            {storyMilestones.map((item) => (
              <article key={item.year} className="rounded-lg border border-burgundy-100 bg-cream-50 p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                  {item.year}
                </p>
                <h3 className="mt-3 font-serif text-3xl text-burgundy-950">{item.title}</h3>
                <p className="mt-4 leading-7 text-burgundy-800">{item.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
