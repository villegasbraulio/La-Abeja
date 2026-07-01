import type { PropsWithChildren, ReactNode } from "react";
import { cn } from "../../lib/utils";

interface PageHeroProps extends PropsWithChildren {
  eyebrow: string;
  title: string;
  description: string;
  aside?: ReactNode;
  className?: string;
  titleClassName?: string;
  descriptionClassName?: string;
  contentClassName?: string;
}

export function PageHero({
  eyebrow,
  title,
  description,
  aside,
  className,
  titleClassName,
  descriptionClassName,
  contentClassName,
  children,
}: PageHeroProps) {
  return (
    <section className={cn("mx-auto max-w-7xl px-4 py-10 sm:px-6 md:py-14", className)}>
      <div className={cn("grid gap-6", aside ? "lg:grid-cols-[1.05fr_0.95fr] lg:items-end" : "grid-cols-1")}>
        <div className={contentClassName}>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-burgundy-600">
            {eyebrow}
          </p>
          <h1
            className={cn(
              "mt-3 max-w-4xl font-serif text-3xl leading-tight text-burgundy-950 sm:text-4xl lg:text-5xl",
              titleClassName,
            )}
          >
            {title}
          </h1>
          <p className={cn("mt-4 max-w-2xl text-base leading-7 text-burgundy-800", descriptionClassName)}>
            {description}
          </p>
          {children ? <div className="mt-6 flex flex-wrap gap-3">{children}</div> : null}
        </div>
        {aside ? (
          <div className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.08)]">
            {aside}
          </div>
        ) : null}
      </div>
    </section>
  );
}
