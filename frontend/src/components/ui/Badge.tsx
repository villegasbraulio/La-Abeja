import type { PropsWithChildren } from "react";
import { cn } from "../../lib/utils";

interface BadgeProps {
  variant?: "gold" | "discount" | "outline";
}

export function Badge({
  children,
  variant = "gold",
}: PropsWithChildren<BadgeProps>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.16em]",
        variant === "gold" && "bg-gold-500/90 text-burgundy-950",
        variant === "discount" && "bg-burgundy-900 text-cream-50",
        variant === "outline" && "border border-cream-50/60 bg-white/15 text-cream-50",
      )}
    >
      {children}
    </span>
  );
}
