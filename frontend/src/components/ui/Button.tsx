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
        "inline-flex items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition-all duration-300 ease-out",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-500 focus-visible:ring-offset-2",
        variant === "primary" && "bg-burgundy-900 text-gold-300 hover:-translate-y-0.5",
        variant === "secondary" && "bg-gold-500 text-burgundy-950 hover:-translate-y-0.5",
        variant === "ghost" && "border border-burgundy-200 text-burgundy-900 hover:bg-burgundy-50",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
