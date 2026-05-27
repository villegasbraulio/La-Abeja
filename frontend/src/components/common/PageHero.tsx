import type { PropsWithChildren, ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "../../lib/utils";

interface PageHeroProps extends PropsWithChildren {
  eyebrow: string;
  title: string;
  description: string;
  aside?: ReactNode;
  className?: string;
}

export function PageHero({
  eyebrow,
  title,
  description,
  aside,
  className,
  children,
}: PageHeroProps) {
  return (
    <section className={cn("mx-auto max-w-7xl px-6 py-16 md:py-20", className)}>
      <div className="grid gap-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-end">
        <div>
          <motion.p
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
            className="text-sm font-semibold uppercase tracking-[0.32em] text-burgundy-600"
          >
            {eyebrow}
          </motion.p>
          <motion.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.12, duration: 0.72, ease: "easeOut" }}
            className="mt-4 max-w-4xl font-serif text-5xl leading-tight text-burgundy-950 md:text-6xl"
          >
            {title}
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.24, duration: 0.72, ease: "easeOut" }}
            className="mt-6 max-w-2xl text-lg leading-8 text-burgundy-800"
          >
            {description}
          </motion.p>
          {children ? <div className="mt-8 flex flex-wrap gap-4">{children}</div> : null}
        </div>
        {aside ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.18, duration: 0.8, ease: "easeOut" }}
            className="rounded-[32px] border border-white/70 bg-white/80 p-6 shadow-velvet"
          >
            {aside}
          </motion.div>
        ) : null}
      </div>
    </section>
  );
}
