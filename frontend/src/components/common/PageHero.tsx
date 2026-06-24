import type { PropsWithChildren, ReactNode } from "react";
import { motion } from "framer-motion";
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
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="text-xs font-semibold uppercase tracking-[0.22em] text-burgundy-600"
          >
            {eyebrow}
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, duration: 0.72, ease: "easeOut" }}
            className={cn(
              "mt-3 max-w-4xl font-serif text-3xl leading-tight text-burgundy-950 sm:text-4xl lg:text-5xl",
              titleClassName,
            )}
          >
            {title}
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.24, duration: 0.72, ease: "easeOut" }}
            className={cn("mt-4 max-w-2xl text-base leading-7 text-burgundy-800", descriptionClassName)}
          >
            {description}
          </motion.p>
          {children ? <div className="mt-6 flex flex-wrap gap-3">{children}</div> : null}
        </div>
        {aside ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.18, duration: 0.8, ease: "easeOut" }}
            className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.08)]"
          >
            {aside}
          </motion.div>
        ) : null}
      </div>
    </section>
  );
}
