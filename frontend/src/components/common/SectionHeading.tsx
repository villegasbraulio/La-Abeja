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
            ? "text-xs font-semibold uppercase tracking-[0.22em] text-gold-300"
            : "text-xs font-semibold uppercase tracking-[0.22em] text-burgundy-600"
        }
      >
        {eyebrow}
      </p>
      <h2
        className={
          tone === "light"
            ? "mt-2 font-serif text-2xl leading-tight text-white sm:text-3xl"
            : "mt-2 font-serif text-2xl leading-tight text-burgundy-950 sm:text-3xl"
        }
      >
        {title}
      </h2>
      {description ? (
        <p
          className={
            tone === "light"
              ? "mt-3 text-base leading-7 text-cream-100/80"
              : "mt-3 text-base leading-7 text-burgundy-800"
          }
        >
          {description}
        </p>
      ) : null}
    </div>
  );
}
