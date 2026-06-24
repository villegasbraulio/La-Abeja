import { useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { cn } from "../../lib/utils";
import { type Toast, useToastStore } from "../../store/toastStore";

const toastStyles = {
  success: {
    icon: CheckCircle2,
    container:
      "border-emerald-200/80 bg-[linear-gradient(135deg,rgba(244,255,248,0.98)_0%,rgba(229,249,237,0.98)_100%)] text-emerald-950",
    iconWrap: "bg-emerald-500 text-white shadow-[0_18px_30px_-20px_rgba(16,185,129,0.85)]",
    progress: "bg-emerald-500/70",
  },
  error: {
    icon: AlertCircle,
    container:
      "border-rose-200/80 bg-[linear-gradient(135deg,rgba(255,247,247,0.98)_0%,rgba(255,235,236,0.98)_100%)] text-rose-950",
    iconWrap: "bg-rose-500 text-white shadow-[0_18px_30px_-20px_rgba(244,63,94,0.85)]",
    progress: "bg-rose-500/70",
  },
  info: {
    icon: Info,
    container:
      "border-burgundy-200/80 bg-[linear-gradient(135deg,rgba(255,251,244,0.98)_0%,rgba(249,239,229,0.98)_100%)] text-burgundy-950",
    iconWrap: "bg-burgundy-900 text-gold-300 shadow-[0_18px_30px_-20px_rgba(79,18,31,0.9)]",
    progress: "bg-gold-500/80",
  },
} as const;

function ToastCard({ toast }: { toast: Toast }) {
  const dismissToast = useToastStore((state) => state.dismissToast);
  const styles = toastStyles[toast.variant];
  const Icon = styles.icon;

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      dismissToast(toast.id);
    }, toast.duration ?? 4200);

    return () => {
      window.clearTimeout(timeout);
    };
  }, [dismissToast, toast.duration, toast.id]);

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -18, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -12, scale: 0.94 }}
      transition={{ duration: 0.22, ease: "easeOut" }}
      className={cn(
        "pointer-events-auto relative overflow-hidden rounded-lg border px-4 py-4 shadow-[0_24px_65px_-34px_rgba(31,27,24,0.45)] backdrop-blur-xl",
        styles.container,
      )}
      role="status"
    >
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "mt-0.5 inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full",
            styles.iconWrap,
          )}
        >
          <Icon className="h-5 w-5" strokeWidth={2} />
        </span>

        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">{toast.title}</p>
          {toast.description ? (
            <p className="mt-1 text-sm leading-6 text-current/75">{toast.description}</p>
          ) : null}
        </div>

        <button
          type="button"
          aria-label="Cerrar notificación"
          onClick={() => dismissToast(toast.id)}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-current/55 transition-colors duration-200 hover:bg-black/5 hover:text-current"
        >
          <X className="h-4 w-4" strokeWidth={2} />
        </button>
      </div>

      <motion.span
        aria-hidden="true"
        initial={{ scaleX: 1 }}
        animate={{ scaleX: 0 }}
        transition={{ duration: (toast.duration ?? 4200) / 1000, ease: "linear" }}
        className={cn(
          "absolute inset-x-0 bottom-0 h-1 origin-left rounded-full",
          styles.progress,
        )}
      />
    </motion.div>
  );
}

export function ToastViewport() {
  const toasts = useToastStore((state) => state.toasts);

  return (
    <div
      aria-live="polite"
      aria-atomic="true"
      className="pointer-events-none fixed inset-x-4 top-20 z-[90] flex flex-col gap-3 sm:left-auto sm:right-6 sm:top-24 sm:w-full sm:max-w-sm"
    >
      <AnimatePresence initial={false}>
        {toasts.map((toast) => (
          <ToastCard key={toast.id} toast={toast} />
        ))}
      </AnimatePresence>
    </div>
  );
}
