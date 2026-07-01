import { Link } from "react-router-dom";
import { PageHero } from "../../components/common/PageHero";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";
import { buildWhatsAppUrl } from "../../lib/contact";
import { giftingCollections } from "../../lib/siteContent";

export function GiftsPage() {
  return (
    <div>
      <PageHero
        eyebrow="Regalos y cajas"
        title="Cajas de vino, obsequios corporativos y selecciones pensadas para celebrar."
        description="Reunimos propuestas para empresas, aniversarios, eventos y agradecimientos con presentación cuidada y asesoramiento personalizado."
        aside={
          <div className="space-y-4 text-burgundy-900">
            <p className="rounded-lg bg-cream-50 px-5 py-4">
              Cajas de 2, 3 y 6 vinos con presentación premium.
            </p>
            <p className="rounded-lg bg-cream-50 px-5 py-4">
              Tarjetas personalizadas, coordinación de entrega y asesoramiento humano.
            </p>
            <p className="rounded-lg bg-cream-50 px-5 py-4">
              Programas especiales para empresas, eventos y celebraciones.
            </p>
          </div>
        }
      >
        <a
          href={buildWhatsAppUrl("Hola, quiero solicitar una propuesta de regalos de Bodega La Abeja.")}
          target="_blank"
          rel="noreferrer"
        >
          <Button>Solicitar propuesta</Button>
        </a>
        <Link to="/vinos">
          <Button variant="ghost">Elegir etiquetas</Button>
        </Link>
      </PageHero>

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-6 lg:grid-cols-3">
          {giftingCollections.map((collection) => (
            <article
              key={collection.title}
              className="rounded-lg border border-burgundy-100 bg-white p-6 shadow-velvet"
            >
              <h2 className="font-serif text-3xl text-burgundy-950">{collection.title}</h2>
              <p className="mt-4 leading-7 text-burgundy-800">{collection.description}</p>
              <ul className="mt-5 space-y-2 text-sm text-burgundy-700">
                {collection.bullets.map((bullet) => (
                  <li key={bullet}>• {bullet}</li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="rounded-lg border border-white/70 bg-burgundy-950 px-8 py-10 text-cream-50 shadow-velvet">
          <SectionHeading
            eyebrow="Gift Concierge"
            title="Un canal dedicado a regalos ayuda a elegir mejor y cuidar cada detalle."
            description="Desde una caja para agasajar hasta un programa corporativo completo, el equipo acompaña la selección, el mensaje y la entrega."
            tone="light"
          />
          <div className="mt-8 flex flex-wrap gap-4">
            <a
              href={buildWhatsAppUrl("Hola, quiero consultar por regalos corporativos de Bodega La Abeja.")}
              target="_blank"
              rel="noreferrer"
            >
              <Button variant="secondary">Hablar por regalos corporativos</Button>
            </a>
            <Link to="/guia-de-compra">
              <Button variant="ghost" className="border-white/30 text-cream-50 hover:bg-white/10">
                Ver logística y envíos
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
