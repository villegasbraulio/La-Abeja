import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { PageHero } from "../../components/common/PageHero";
import { SectionHeading } from "../../components/common/SectionHeading";
import { Button } from "../../components/ui/Button";
import { contactChannels } from "../../lib/siteContent";

const inquiryOptions = [
  { value: "visita", label: "Reserva de visita" },
  { value: "evento", label: "Evento privado" },
  { value: "regalos", label: "Regalos y cajas" },
  { value: "corporativo", label: "Programa corporativo" },
  { value: "envios", label: "Envios o retiro" },
  { value: "general", label: "Consulta general" },
];

export function ContactPage() {
  const [searchParams] = useSearchParams();
  const defaultInquiry = searchParams.get("tipo") ?? "general";
  const [submitted, setSubmitted] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitted(true);
  }

  return (
    <div>
      <PageHero
        eyebrow="Contacto"
        title="Un canal directo para consultas, reservas y pedidos especiales."
        description="Canales visibles y un formulario simple para ordenar consultas sobre visitas, regalos, envios y eventos privados."
        aside={
          <div className="space-y-4">
            {contactChannels.map((channel) => (
              <div key={channel.label} className="rounded-[24px] bg-cream-50 p-4 text-burgundy-900">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                  {channel.label}
                </p>
                <p className="mt-2 text-lg font-semibold">{channel.value}</p>
                <p className="mt-2 text-sm leading-6 text-burgundy-700">{channel.note}</p>
              </div>
            ))}
          </div>
        }
      />

      <section className="mx-auto max-w-7xl px-6 py-8">
        <div className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
            <SectionHeading
              eyebrow="Formulario de contacto"
              title="Contanos que necesitas y te ayudamos a resolverlo."
            />
            <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
              <div className="grid gap-5 md:grid-cols-2">
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Nombre</span>
                  <input
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                    name="first_name"
                    placeholder="Tu nombre"
                    required
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Email</span>
                  <input
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                    name="email"
                    placeholder="tuemail@ejemplo.com"
                    type="email"
                    required
                  />
                </label>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Telefono</span>
                  <input
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                    name="phone"
                    placeholder="+54 260..."
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Motivo</span>
                  <select
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                    name="inquiry"
                    defaultValue={defaultInquiry}
                  >
                    {inquiryOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Mensaje</span>
                <textarea
                  className="min-h-36 rounded-[24px] border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                  name="message"
                  placeholder="Contanos que necesitas: visita, regalo, compra o evento."
                  required
                />
              </label>

              <div className="flex flex-wrap items-center gap-4">
                <Button type="submit">Enviar consulta</Button>
                <p className="text-sm text-burgundy-600">
                  {submitted
                    ? "Recibimos tu consulta. El equipo te va a responder dentro del horario comercial."
                    : "Respuesta esperada dentro del horario comercial del concierge."}
                </p>
              </div>
            </form>
          </div>

          <div className="rounded-[32px] border border-white/70 bg-burgundy-950 p-8 text-cream-50 shadow-velvet">
            <SectionHeading
              eyebrow="Atencion personalizada"
              title="Regalos, eventos y compras de volumen necesitan una conversacion propia."
              description="Cuando el cliente encuentra contacto, direccion y asistencia clara, la experiencia gana confianza desde el primer mensaje."
              tone="light"
            />
            <ul className="mt-8 space-y-3 text-cream-100/80">
              <li>• Ayuda a capturar demanda corporativa y privada.</li>
              <li>• Ordena mejor el flujo para visitas y regalos.</li>
              <li>• Refuerza confianza con direccion, horario y soporte directo.</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
