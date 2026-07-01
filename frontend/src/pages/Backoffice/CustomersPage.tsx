import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { backofficeApi } from "../../api/backoffice";
import { Button } from "../../components/ui/Button";
import { downloadBlob } from "../../lib/download";
import { formatARS, formatDate } from "../../lib/utils";

export function BackofficeCustomersPage() {
  const [search, setSearch] = useState("");
  const customersQuery = useQuery({
    queryKey: ["backoffice-customers", search],
    queryFn: () => backofficeApi.customers.list({ search: search.trim() || undefined }),
  });
  const customers = useMemo(() => customersQuery.data?.results ?? [], [customersQuery.data]);

  async function handleExport() {
    downloadBlob(await backofficeApi.customers.exportCsv(), "clientes.csv");
  }

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)] md:p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
              Clientes
            </p>
            <h1 className="mt-1.5 text-2xl font-semibold text-burgundy-950">Compradores</h1>
          </div>
          <Button variant="ghost" onClick={handleExport}>
            <Download className="h-4 w-4" strokeWidth={1.9} />
            Exportar CSV
          </Button>
        </div>
      </section>

      <section className="rounded-lg border border-burgundy-100 bg-white p-5 shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
        <label className="space-y-2 text-sm font-semibold text-burgundy-900">
          Buscar cliente
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="w-full rounded-2xl border border-burgundy-100 bg-cream-50 px-4 py-3 text-sm text-burgundy-950 outline-none transition focus:border-burgundy-300"
            placeholder="email, nombre o teléfono"
          />
        </label>
      </section>

      <section className="overflow-hidden rounded-lg border border-burgundy-100 bg-white shadow-[0_16px_48px_rgba(66,13,21,0.07)]">
        <div className="grid grid-cols-[minmax(220px,1fr)_140px_150px_160px] bg-cream-50 px-4 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
          <span>Cliente</span>
          <span>Pedidos</span>
          <span>Total</span>
          <span>Última compra</span>
        </div>
        {customers.map((customer) => (
          <article
            key={customer.id}
            className="grid grid-cols-[minmax(220px,1fr)_140px_150px_160px] items-center border-t border-burgundy-100 px-4 py-4 text-sm text-burgundy-800"
          >
            <div>
              <p className="font-semibold text-burgundy-950">{customer.full_name || customer.email}</p>
              <p className="mt-1">{customer.email}</p>
              {customer.phone ? <p className="mt-1">{customer.phone}</p> : null}
            </div>
            <p>{customer.orders_count}</p>
            <p>{formatARS(customer.total_spent ?? "0")}</p>
            <p>{customer.last_order_at ? formatDate(customer.last_order_at) : "Sin compras"}</p>
          </article>
        ))}
        {customersQuery.isLoading ? <p className="p-5 text-burgundy-700">Cargando clientes...</p> : null}
        {!customersQuery.isLoading && customers.length === 0 ? (
          <p className="p-5 text-burgundy-700">No encontramos clientes con esa búsqueda.</p>
        ) : null}
      </section>
    </div>
  );
}
