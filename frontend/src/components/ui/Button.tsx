import type { ButtonHTMLAttributes, PropsWithChildren } from "react";
import { cn } from "../../lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost";
}

export function Button({
  children,
  className,
  variant = "primary",
  ...props
}: PropsWithChildren<ButtonProps>) {
  return (
    <button
      className={cn(
        "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors duration-200 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-500 focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-55",
        variant === "primary" && "bg-burgundy-900 text-gold-300 hover:bg-burgundy-800",
        variant === "secondary" && "bg-gold-500 text-burgundy-950 hover:bg-gold-400",
        variant === "ghost" && "border border-burgundy-200 bg-white/70 text-burgundy-900 hover:bg-burgundy-50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
