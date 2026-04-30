interface SectionHeadingProps {
  eyebrow: string;
  title: string;
  description?: string;
  tone?: "dark" | "light";
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  tone = "dark",
}: SectionHeadingProps) {
  return (
    <div className="max-w-3xl">
      <p
        className={
          tone === "light"
            ? "text-sm font-semibold uppercase tracking-[0.3em] text-gold-300"
            : "text-sm font-semibold uppercase tracking-[0.3em] text-burgundy-600"
        }
      >
        {eyebrow}
      </p>
      <h2
        className={
          tone === "light"
            ? "mt-3 font-serif text-4xl leading-tight text-white md:text-5xl"
            : "mt-3 font-serif text-4xl leading-tight text-burgundy-950 md:text-5xl"
        }
      >
        {title}
      </h2>
      {description ? (
        <p
          className={
            tone === "light"
              ? "mt-4 text-lg leading-8 text-cream-100/80"
              : "mt-4 text-lg leading-8 text-burgundy-800"
          }
        >
          {description}
        </p>
      ) : null}
    </div>
  );
}
