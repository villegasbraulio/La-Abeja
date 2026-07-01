import { type FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import { formatARS, formatDate } from "../../lib/utils";
import type { BackofficePromoCodePayload } from "../../types/backoffice";

const discountTypes = [
  { value: "percentage", label: "Porcentaje" },
  { value: "fixed", label: "Monto fijo" },
  { value: "free_shipping", label: "Envío gratis" },
] as const;

function defaultDate(daysFromNow: number) {
  return new Date(Date.now() + daysFromNow * 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
}

export function BackofficePromoCodesPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<BackofficePromoCodePayload>({
    code: "",
    discount_type: "percentage",
    discount_value: "10.00",
    min_order_amount: "0.00",
    max_uses: null,
    valid_from: defaultDate(0),
    valid_until: defaultDate(30),
    is_active: true,
  });
  const promoCodesQuery = useQuery({
    queryKey: ["backoffice-promo-codes"],
    queryFn: backofficeApi.promoCodes.list,
  });
  const promoCodes = useMemo(() => promoCodesQuery.data?.results ?? [], [promoCodesQuery.data]);

  const createMutation = useMutation({
    mutationFn: backofficeApi.promoCodes.create,
    onSuccess: () => {
      setForm((current) => ({ ...current, code: "" }));
      void queryClient.invalidateQueries({ queryKey: ["backoffice-promo-codes"] });
    },
  });
  const updateMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      backofficeApi.promoCodes.update(id, { is_active }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["backoffice-promo-codes"] }),
  });
  const removeMutation = useMutation({
    mutationFn: backofficeApi.promoCodes.remove,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["backoffice-promo-codes"] }),
  });

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createMutation.mutate({
      ...form,
      code: form.code.trim().toUpperCase(),
      max_uses: form.max_uses || null,
    });
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
          Promociones
        </p>
        <h1 className="mt-1.5 text-2xl font-semibold text-burgundy-950">Cupones</h1>
      </section>

      <form
        onSubmit={handleSubmit}
        className="grid gap-4 rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] lg:grid-cols-4"
      >
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Código
          <input
            value={form.code}
            onChange={(event) => setForm((current) => ({ ...current, code: event.target.value }))}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none"
            placeholder="ABEJA10"
            required
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Tipo
          <select
            value={form.discount_type}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                discount_type: event.target.value as BackofficePromoCodePayload["discount_type"],
              }))
            }
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none"
          >
            {discountTypes.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Descuento
          <input
            type="number"
            step="0.01"
            value={form.discount_value}
            onChange={(event) => setForm((current) => ({ ...current, discount_value: event.target.value }))}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none"
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Mínimo
          <input
            type="number"
            step="0.01"
            value={form.min_order_amount}
            onChange={(event) => setForm((current) => ({ ...current, min_order_amount: event.target.value }))}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none"
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Usos máximos
          <input
            type="number"
            value={form.max_uses ?? ""}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                max_uses: event.target.value ? Number(event.target.value) : null,
              }))
            }
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none"
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Desde
          <input
            type="datetime-local"
            value={form.valid_from}
            onChange={(event) => setForm((current) => ({ ...current, valid_from: event.target.value }))}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none"
          />
        </label>
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Hasta
          <input
            type="datetime-local"
            value={form.valid_until}
            onChange={(event) => setForm((current) => ({ ...current, valid_until: event.target.value }))}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none"
          />
        </label>
        <div className="flex items-end">
          <Button type="submit" className="w-full" disabled={createMutation.isPending}>
            Crear cupón
          </Button>
        </div>
      </form>

      <section className="overflow-hidden rounded-lg border border-burgundy-100 bg-white shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
        <div className="grid grid-cols-[minmax(160px,1fr)_130px_130px_130px_160px_170px] bg-cream-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
          <span>Código</span>
          <span>Tipo</span>
          <span>Valor</span>
          <span>Usos</span>
          <span>Vence</span>
          <span className="text-right">Acción</span>
        </div>
        {promoCodes.map((promoCode) => (
          <article
            key={promoCode.id}
            className="grid grid-cols-[minmax(160px,1fr)_130px_130px_130px_160px_170px] items-center border-t border-burgundy-100 px-4 py-4 text-sm text-burgundy-800"
          >
            <div>
              <p className="font-semibold text-burgundy-950">{promoCode.code}</p>
              <p className="mt-1">{promoCode.is_active ? "Activo" : "Pausado"}</p>
            </div>
            <p>{discountTypes.find((type) => type.value === promoCode.discount_type)?.label}</p>
            <p>
              {promoCode.discount_type === "percentage"
                ? `${Number(promoCode.discount_value)}%`
                : formatARS(promoCode.discount_value)}
            </p>
            <p>
              {promoCode.used_count}
              {promoCode.max_uses ? `/${promoCode.max_uses}` : ""}
            </p>
            <p>{formatDate(promoCode.valid_until)}</p>
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                className="min-h-9 px-3 py-1.5"
                onClick={() =>
                  updateMutation.mutate({ id: promoCode.id, is_active: !promoCode.is_active })
                }
              >
                {promoCode.is_active ? "Pausar" : "Activar"}
              </Button>
              <Button
                variant="secondary"
                className="min-h-9 px-3 py-1.5"
                onClick={() => removeMutation.mutate(promoCode.id)}
              >
                <Trash2 className="h-4 w-4" strokeWidth={1.9} />
              </Button>
            </div>
          </article>
        ))}
        {promoCodesQuery.isLoading ? <p className="p-5 text-burgundy-700">Cargando cupones...</p> : null}
        {!promoCodesQuery.isLoading && promoCodes.length === 0 ? (
          <p className="p-5 text-burgundy-700">Todavía no hay cupones creados.</p>
        ) : null}
      </section>
    </div>
  );
}
