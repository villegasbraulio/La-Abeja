import type {
  ComponentPropsWithoutRef,
  HTMLAttributes,
  InputHTMLAttributes,
  PropsWithChildren,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";
import { cn } from "../../lib/utils";

interface HeroStat {
  label: string;
  value: number | string;
}

interface BackofficeHeroProps {
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
  stats?: HeroStat[];
}

interface BackofficePanelHeaderProps {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}

interface BackofficeFieldProps {
  label: string;
  hint?: string;
  className?: string;
  children: ReactNode;
}

type InputProps = InputHTMLAttributes<HTMLInputElement>;
type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;
type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

type BadgeTone = "default" | "soft" | "gold" | "success" | "warning" | "dark";
type MessageTone = "default" | "success" | "danger";

const fieldBaseClasses =
  "w-full rounded-[20px] border border-burgundy-200 bg-white px-4 py-3.5 text-sm text-burgundy-950 outline-none transition placeholder:text-burgundy-400 focus:border-burgundy-400 focus:ring-4 focus:ring-burgundy-100/80";

export function BackofficeHero({
  eyebrow,
  title,
  description,
  actions,
  stats = [],
}: BackofficeHeroProps) {
  return (
    <section className="relative overflow-hidden rounded-[34px] border border-burgundy-100 bg-white px-6 py-7 shadow-velvet md:px-8 md:py-8">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(200,169,110,0.16),transparent_34%),radial-gradient(circle_at_bottom_right,rgba(114,47,55,0.08),transparent_36%)]" />
      <div className="relative flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
            {eyebrow}
          </p>
          <h3 className="mt-3 font-serif text-4xl leading-tight text-burgundy-950">{title}</h3>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-burgundy-800">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap gap-3 xl:justify-end">{actions}</div> : null}
      </div>

      {stats.length > 0 ? (
        <div className="relative mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {stats.map((stat) => (
            <article
              key={stat.label}
              className="rounded-[24px] border border-burgundy-100/80 bg-white/80 px-4 py-4 backdrop-blur"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                {stat.label}
              </p>
              <p className="mt-3 font-serif text-3xl text-burgundy-950">{stat.value}</p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

export function BackofficePanel({
  children,
  className,
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return (
    <section
      className={cn(
        "rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet md:p-7",
        className,
      )}
      {...props}
    >
      {children}
    </section>
  );
}

export function BackofficePanelHeader({
  eyebrow,
  title,
  description,
  actions,
}: BackofficePanelHeaderProps) {
  return (
    <div className="flex flex-col gap-4 border-b border-burgundy-100 pb-5 md:flex-row md:items-end md:justify-between">
      <div className="max-w-2xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
          {eyebrow}
        </p>
        <h4 className="mt-2 font-serif text-3xl text-burgundy-950">{title}</h4>
        {description ? (
          <p className="mt-3 text-sm leading-7 text-burgundy-800">{description}</p>
        ) : null}
      </div>
      {actions ? <div className="flex flex-wrap gap-3">{actions}</div> : null}
    </div>
  );
}

export function BackofficeSectionCard({
  children,
  className,
  ...props
}: PropsWithChildren<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={cn(
        "rounded-[28px] border border-burgundy-100 bg-cream-50/80 p-5 md:p-6",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function BackofficeSectionHeading({
  eyebrow,
  title,
  description,
}: Pick<BackofficePanelHeaderProps, "eyebrow" | "title" | "description">) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
        {eyebrow}
      </p>
      <h5 className="mt-2 font-serif text-2xl text-burgundy-950">{title}</h5>
      {description ? (
        <p className="mt-3 max-w-2xl text-sm leading-7 text-burgundy-800">{description}</p>
      ) : null}
    </div>
  );
}

export function BackofficeField({ label, hint, className, children }: BackofficeFieldProps) {
  return (
    <label className={cn("grid gap-2.5", className)}>
      <span className="text-sm font-semibold text-burgundy-900">{label}</span>
      {children}
      {hint ? <span className="text-xs leading-6 text-burgundy-600">{hint}</span> : null}
    </label>
  );
}

export function BackofficeInput({ className, ...props }: InputProps) {
  return <input className={cn(fieldBaseClasses, "min-h-[54px]", className)} {...props} />;
}

export function BackofficeSelect({ className, ...props }: SelectProps) {
  return <select className={cn(fieldBaseClasses, "min-h-[54px]", className)} {...props} />;
}

export function BackofficeTextarea({ className, ...props }: TextareaProps) {
  return <textarea className={cn(fieldBaseClasses, "min-h-[132px] resize-y", className)} {...props} />;
}

export function BackofficeBadge({
  children,
  tone = "default",
  className,
}: PropsWithChildren<{ tone?: BadgeTone; className?: string }>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em]",
        tone === "default" && "border-burgundy-100 bg-white text-burgundy-800",
        tone === "soft" && "border-burgundy-100 bg-cream-50 text-burgundy-700",
        tone === "gold" && "border-gold-500/30 bg-gold-300/20 text-gold-700",
        tone === "success" && "border-emerald-200 bg-emerald-50 text-emerald-700",
        tone === "warning" && "border-amber-200 bg-amber-50 text-amber-700",
        tone === "dark" && "border-burgundy-900 bg-burgundy-950 text-cream-50",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function BackofficeMessage({
  children,
  tone = "default",
}: PropsWithChildren<{ tone?: MessageTone }>) {
  return (
    <div
      className={cn(
        "rounded-[22px] border px-4 py-3 text-sm leading-7",
        tone === "default" && "border-burgundy-200 bg-burgundy-50 text-burgundy-800",
        tone === "success" && "border-emerald-200 bg-emerald-50 text-emerald-800",
        tone === "danger" && "border-rose-200 bg-rose-50 text-rose-800",
      )}
    >
      {children}
    </div>
  );
}

export function BackofficeCheckboxCard({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: ComponentPropsWithoutRef<"input">["onChange"];
  label: string;
  description: string;
}) {
  return (
    <label
      className={cn(
        "flex h-full cursor-pointer items-start gap-3 rounded-[24px] border px-4 py-4 transition",
        checked
          ? "border-burgundy-300 bg-white text-burgundy-950 shadow-[0_18px_40px_rgba(66,13,21,0.08)]"
          : "border-burgundy-100 bg-cream-50 text-burgundy-900",
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="mt-1 h-4 w-4 accent-burgundy-900"
      />
      <span className="min-w-0">
        <span className="block text-sm font-semibold">{label}</span>
        <span className="mt-1 block text-sm leading-6 text-current/70">{description}</span>
      </span>
    </label>
  );
}

export function BackofficeEmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-[24px] border border-dashed border-burgundy-200 bg-cream-50/80 px-5 py-6 text-burgundy-800">
      <p className="font-semibold text-burgundy-950">{title}</p>
      <p className="mt-2 text-sm leading-7">{description}</p>
    </div>
  );
}
