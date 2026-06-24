import { useState, type FormEvent } from "react";
import { Button } from "../ui/Button";

interface NewsletterCardProps {
  title?: string;
  description?: string;
}

export function NewsletterCard({
  title = "Sumate a la lista privada de novedades",
  description = "Recibi lanzamientos, agendas de visitas, recomendaciones de maridaje y regalos con criterio curado.",
}: NewsletterCardProps) {
  const [email, setEmail] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitted(true);
    setEmail("");
  }

  return (
    <div className="rounded-lg border border-burgundy-100 bg-white p-8 shadow-velvet">
      <p className="text-sm font-semibold uppercase tracking-[0.26em] text-burgundy-500">
        Newsletter
      </p>
      <h3 className="mt-3 font-serif text-3xl text-burgundy-950">{title}</h3>
      <p className="mt-4 max-w-2xl text-burgundy-800">{description}</p>
      <form className="mt-8 flex flex-col gap-3 md:flex-row" onSubmit={handleSubmit}>
        <input
          type="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="tuemail@ejemplo.com"
          className="w-full rounded-full border border-burgundy-200 bg-cream-50 px-5 py-3 text-burgundy-950 outline-none placeholder:text-burgundy-400 focus:border-burgundy-400"
          required
        />
        <Button type="submit">Quiero recibir novedades</Button>
      </form>
      <p className="mt-3 text-sm text-burgundy-600">
        {isSubmitted
          ? "Gracias por sumarte. Te vamos a escribir con novedades, lanzamientos y fechas destacadas."
          : "Sin spam: solo novedades utiles, agendas, etiquetas destacadas y ventanas especiales de compra."}
      </p>
    </div>
  );
}
