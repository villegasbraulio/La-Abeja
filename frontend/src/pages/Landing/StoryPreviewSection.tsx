import { Link } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { SectionHeading } from "../../components/common/SectionHeading";
import { storyMilestones } from "../../lib/siteContent";

export function StoryPreviewSection() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-20">
      <div className="rounded-lg border border-white/70 bg-burgundy-950 px-8 py-10 text-cream-50 shadow-velvet md:px-10 md:py-12">
        <div className="grid gap-10 lg:grid-cols-[0.85fr_1.15fr]">
          <SectionHeading
            eyebrow="Nuestra historia"
            title="Una historia de origen, oficio y hospitalidad que sigue viva en cada visita."
            description="La colección se entiende mejor cuando se la conecta con el territorio, la cava y el carácter de la bodega."
            tone="light"
          />
          <div className="space-y-5">
            {storyMilestones.map((item) => (
              <div key={item.year} className="rounded-lg border border-white/10 bg-white/5 p-6">
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-gold-300">
                  {item.year}
                </p>
                <h3 className="mt-2 font-serif text-2xl text-white">{item.title}</h3>
                <p className="mt-3 leading-7 text-cream-100/80">{item.description}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="mt-8">
          <Link to="/historia">
            <Button variant="secondary">Explorar la historia completa</Button>
          </Link>
        </div>
      </div>
    </section>
  );
}
