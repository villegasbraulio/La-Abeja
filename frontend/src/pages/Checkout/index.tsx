import { type FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { AxiosError } from "axios";
import { Link } from "react-router-dom";
import { authApi } from "../../api/auth";
import { ordersApi } from "../../api/orders";
import { paymentsApi } from "../../api/payments";
import { Button } from "../../components/ui/Button";
import { useCart } from "../../hooks/useCart";
import { applyWineImageFallback, wineImageSrc } from "../../lib/assets";
import { formatARS, formatDate } from "../../lib/utils";
import { useAuthStore } from "../../store/authStore";
import type { Order, ShippingMethod } from "../../types/orders";

export function CheckoutPage() {
  const { items, subtotal, subtotalFormatted } = useCart();
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  const setSession = useAuthStore((state) => state.setSession);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authError, setAuthError] = useState<string | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [createdOrder, setCreatedOrder] = useState<Order | null>(null);
  const [loginForm, setLoginForm] = useState({
    email: "",
    password: "",
  });
  const [registerForm, setRegisterForm] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    password: "",
  });
  const [shippingForm, setShippingForm] = useState({
    recipient_name: user?.full_name || "",
    street: "",
    number: "",
    floor_apt: "",
    city: "San Rafael",
    province: "Mendoza",
    postal_code: "5600",
    country: "Argentina",
    phone: user?.phone || "",
    shipping_method: "standard" as ShippingMethod,
    notes: "",
  });

  const quoteAddressReady = Boolean(
    shippingForm.city.trim() &&
      shippingForm.province.trim() &&
      shippingForm.postal_code.trim() &&
      shippingForm.country.trim(),
  );

  const shippingQuoteQuery = useQuery({
    queryKey: [
      "checkout-shipping-quotes",
      items.map((item) => `${item.wineId}:${item.quantity}`),
      shippingForm.city,
      shippingForm.province,
      shippingForm.postal_code,
      shippingForm.country,
    ],
    queryFn: () =>
      ordersApi.quoteShipping({
        items: items.map((item) => ({
          wine_id: item.wineId,
          quantity: item.quantity,
        })),
        shipping_address: {
          city: shippingForm.city,
          province: shippingForm.province,
          postal_code: shippingForm.postal_code,
          country: shippingForm.country,
        },
      }),
    enabled: items.length > 0 && quoteAddressReady,
    staleTime: 60_000,
  });

  const shippingOptions = useMemo(
    () => shippingQuoteQuery.data?.quotes ?? [],
    [shippingQuoteQuery.data?.quotes],
  );

  useEffect(() => {
    if (shippingOptions.length === 0) {
      return;
    }
    if (shippingOptions.some((option) => option.shipping_method === shippingForm.shipping_method)) {
      return;
    }
    setShippingForm((current) => ({
      ...current,
      shipping_method: shippingOptions[0].shipping_method,
    }));
  }, [shippingOptions, shippingForm.shipping_method]);

  const selectedShipping = useMemo(
    () =>
      shippingOptions.find((option) => option.shipping_method === shippingForm.shipping_method) ??
      null,
    [shippingOptions, shippingForm.shipping_method],
  );

  const shippingCost = selectedShipping ? Number.parseFloat(selectedShipping.shipping_cost) : 0;
  const total = subtotal + shippingCost;

  const loginMutation = useMutation({
    mutationFn: () => authApi.login(loginForm),
    onSuccess: (session) => {
      setSession({
        accessToken: session.access,
        refreshToken: session.refresh,
        user: session.user,
      });
      setShippingForm((current) => ({
        ...current,
        recipient_name: session.user.full_name || `${session.user.first_name} ${session.user.last_name}`.trim(),
        phone: session.user.phone || current.phone,
      }));
      setAuthError(null);
    },
    onError: (error) => {
      const axiosError = error as AxiosError<{ detail?: string }>;
      setAuthError(
        axiosError.response?.data?.detail ??
          "No pudimos iniciar sesión. Revisá el email y la contraseña.",
      );
    },
  });

  const registerMutation = useMutation({
    mutationFn: () =>
      authApi.register({
        ...registerForm,
        newsletter_subscribed: true,
        preferred_varietals: [],
      }),
    onSuccess: (session) => {
      setSession({
        accessToken: session.access,
        refreshToken: session.refresh,
        user: session.user,
      });
      setShippingForm((current) => ({
        ...current,
        recipient_name: session.user.full_name || `${session.user.first_name} ${session.user.last_name}`.trim(),
        phone: session.user.phone || registerForm.phone,
      }));
      setAuthError(null);
    },
    onError: (error) => {
      const axiosError = error as AxiosError<{ email?: string[]; password?: string[] }>;
      setAuthError(
        axiosError.response?.data?.email?.[0] ??
          axiosError.response?.data?.password?.[0] ??
          "No pudimos crear la cuenta para continuar con la compra.",
      );
    },
  });

  const shippingQuoteError =
    (shippingQuoteQuery.error as AxiosError<{ detail?: string; shipping_address?: string[] }> | null)
      ?.response?.data?.detail ??
    (shippingQuoteQuery.error as AxiosError<{ detail?: string; shipping_address?: string[] }> | null)
      ?.response?.data?.shipping_address?.[0] ??
    (shippingQuoteQuery.error instanceof Error
      ? shippingQuoteQuery.error.message
      : null);

  const checkoutMutation = useMutation({
    mutationFn: async () => {
      if (!selectedShipping) {
        throw new Error("Necesitamos una cotización válida antes de enviarte a Mercado Pago.");
      }
      const order = await ordersApi.create({
        items: items.map((item) => ({
          wine_id: item.wineId,
          quantity: item.quantity,
        })),
        shipping_method: shippingForm.shipping_method,
        shipping_address: {
          recipient_name: shippingForm.recipient_name,
          street: shippingForm.street,
          number: shippingForm.number,
          floor_apt: shippingForm.floor_apt,
          city: shippingForm.city,
          province: shippingForm.province,
          postal_code: shippingForm.postal_code,
          country: shippingForm.country,
          phone: shippingForm.phone,
        },
        notes: shippingForm.notes,
      });
      setCreatedOrder(order);
      const preference = await paymentsApi.createPreference(order.id);
      const redirectUrl = preference.init_point ?? preference.sandbox_init_point;
      if (!redirectUrl) {
        throw new Error("Mercado Pago no devolvió una URL válida para continuar el pago.");
      }
      return redirectUrl;
    },
    onSuccess: (redirectUrl) => {
      window.location.assign(redirectUrl);
    },
    onError: (error) => {
      if (error instanceof Error) {
        setPaymentError(error.message);
        return;
      }
      const axiosError = error as AxiosError<{ detail?: string }>;
      setPaymentError(
        axiosError.response?.data?.detail ??
          "No pudimos generar la orden o iniciar el pago en Mercado Pago.",
      );
    },
  });

  function handleCustomerAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError(null);
    if (authMode === "login") {
      loginMutation.mutate();
      return;
    }
    registerMutation.mutate();
  }

  function handleCheckoutSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPaymentError(null);
    checkoutMutation.mutate();
  }

  if (items.length === 0) {
    return (
      <section className="mx-auto max-w-4xl px-6 py-16">
        <div className="rounded-[32px] border border-burgundy-100 bg-white p-10 text-center shadow-velvet">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
            Checkout
          </p>
          <h1 className="mt-3 font-serif text-5xl text-burgundy-950">
            No hay vinos para procesar.
          </h1>
          <p className="mt-4 text-burgundy-800">
            Sumá etiquetas al carrito y después volvés para cerrar la compra.
          </p>
          <Link to="/vinos" className="mt-8 inline-flex">
            <Button>Ir al catálogo</Button>
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-7xl px-6 py-16">
      <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
            Checkout
          </p>
          <h1 className="mt-2 font-serif text-5xl text-burgundy-950">
            Cerrá la compra y pagá con Mercado Pago.
          </h1>
        </div>
        <Link to="/carrito">
          <Button variant="ghost">Volver al carrito</Button>
        </Link>
      </div>

      <div className="grid gap-8 xl:grid-cols-[1.05fr_0.95fr]">
        <div className="space-y-6">
          {!accessToken || !user ? (
            <section className="rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet">
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  className={`rounded-full px-4 py-2 text-sm font-semibold ${
                    authMode === "login"
                      ? "bg-burgundy-900 text-gold-300"
                      : "bg-cream-50 text-burgundy-800"
                  }`}
                  onClick={() => setAuthMode("login")}
                >
                  Iniciar sesión
                </button>
                <button
                  type="button"
                  className={`rounded-full px-4 py-2 text-sm font-semibold ${
                    authMode === "register"
                      ? "bg-burgundy-900 text-gold-300"
                      : "bg-cream-50 text-burgundy-800"
                  }`}
                  onClick={() => setAuthMode("register")}
                >
                  Crear cuenta
                </button>
              </div>

              <h2 className="mt-6 font-serif text-3xl text-burgundy-950">
                Necesitamos una cuenta para crear la orden.
              </h2>
              <p className="mt-3 text-burgundy-700">
                En esta fase 1 dejamos el checkout real con órdenes persistidas e historial de
                compra. Por eso el pedido queda asociado a un cliente autenticado.
              </p>

              <form className="mt-8 space-y-5" onSubmit={handleCustomerAuthSubmit}>
                {authMode === "register" ? (
                  <div className="grid gap-5 md:grid-cols-2">
                    <label className="grid gap-2">
                      <span className="text-sm font-semibold text-burgundy-800">Nombre</span>
                      <input
                        value={registerForm.first_name}
                        onChange={(event) =>
                          setRegisterForm((current) => ({
                            ...current,
                            first_name: event.target.value,
                          }))
                        }
                        className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                        required
                      />
                    </label>
                    <label className="grid gap-2">
                      <span className="text-sm font-semibold text-burgundy-800">Apellido</span>
                      <input
                        value={registerForm.last_name}
                        onChange={(event) =>
                          setRegisterForm((current) => ({
                            ...current,
                            last_name: event.target.value,
                          }))
                        }
                        className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                        required
                      />
                    </label>
                    <label className="grid gap-2">
                      <span className="text-sm font-semibold text-burgundy-800">Email</span>
                      <input
                        type="email"
                        value={registerForm.email}
                        onChange={(event) =>
                          setRegisterForm((current) => ({
                            ...current,
                            email: event.target.value,
                          }))
                        }
                        className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                        required
                      />
                    </label>
                    <label className="grid gap-2">
                      <span className="text-sm font-semibold text-burgundy-800">Teléfono</span>
                      <input
                        value={registerForm.phone}
                        onChange={(event) =>
                          setRegisterForm((current) => ({
                            ...current,
                            phone: event.target.value,
                          }))
                        }
                        className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                      />
                    </label>
                    <label className="grid gap-2 md:col-span-2">
                      <span className="text-sm font-semibold text-burgundy-800">Contraseña</span>
                      <input
                        type="password"
                        value={registerForm.password}
                        onChange={(event) =>
                          setRegisterForm((current) => ({
                            ...current,
                            password: event.target.value,
                          }))
                        }
                        className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                        required
                      />
                    </label>
                  </div>
                ) : (
                  <div className="grid gap-5 md:grid-cols-2">
                    <label className="grid gap-2 md:col-span-2">
                      <span className="text-sm font-semibold text-burgundy-800">Email</span>
                      <input
                        type="email"
                        value={loginForm.email}
                        onChange={(event) =>
                          setLoginForm((current) => ({
                            ...current,
                            email: event.target.value,
                          }))
                        }
                        className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                        required
                      />
                    </label>
                    <label className="grid gap-2 md:col-span-2">
                      <span className="text-sm font-semibold text-burgundy-800">Contraseña</span>
                      <input
                        type="password"
                        value={loginForm.password}
                        onChange={(event) =>
                          setLoginForm((current) => ({
                            ...current,
                            password: event.target.value,
                          }))
                        }
                        className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                        required
                      />
                    </label>
                  </div>
                )}

                {authError ? (
                  <div className="rounded-[22px] border border-burgundy-200 bg-burgundy-50 px-4 py-3 text-sm text-burgundy-800">
                    {authError}
                  </div>
                ) : null}

                <Button
                  className="w-full"
                  type="submit"
                  disabled={loginMutation.isPending || registerMutation.isPending}
                >
                  {authMode === "login"
                    ? loginMutation.isPending
                      ? "Ingresando..."
                      : "Continuar con esta cuenta"
                    : registerMutation.isPending
                      ? "Creando cuenta..."
                      : "Crear cuenta y seguir"}
                </Button>
              </form>
            </section>
          ) : (
            <form
              className="space-y-6 rounded-[32px] border border-burgundy-100 bg-white p-8 shadow-velvet"
              onSubmit={handleCheckoutSubmit}
            >
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
                  Datos de entrega
                </p>
                <h2 className="mt-3 font-serif text-3xl text-burgundy-950">
                  Tu orden va a quedar a nombre de {user.full_name || user.email}.
                </h2>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <label className="grid gap-2 md:col-span-2">
                  <span className="text-sm font-semibold text-burgundy-800">
                    Nombre del destinatario
                  </span>
                  <input
                    value={shippingForm.recipient_name}
                    onChange={(event) =>
                      setShippingForm((current) => ({
                        ...current,
                        recipient_name: event.target.value,
                      }))
                    }
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                    required
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Calle</span>
                  <input
                    value={shippingForm.street}
                    onChange={(event) =>
                      setShippingForm((current) => ({ ...current, street: event.target.value }))
                    }
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                    required
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Número</span>
                  <input
                    value={shippingForm.number}
                    onChange={(event) =>
                      setShippingForm((current) => ({ ...current, number: event.target.value }))
                    }
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                    required
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Piso / dpto.</span>
                  <input
                    value={shippingForm.floor_apt}
                    onChange={(event) =>
                      setShippingForm((current) => ({
                        ...current,
                        floor_apt: event.target.value,
                      }))
                    }
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Ciudad</span>
                  <input
                    value={shippingForm.city}
                    onChange={(event) =>
                      setShippingForm((current) => ({ ...current, city: event.target.value }))
                    }
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                    required
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Provincia</span>
                  <input
                    value={shippingForm.province}
                    onChange={(event) =>
                      setShippingForm((current) => ({
                        ...current,
                        province: event.target.value,
                      }))
                    }
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                    required
                  />
                </label>
                <label className="grid gap-2">
                  <span className="text-sm font-semibold text-burgundy-800">Código postal</span>
                  <input
                    value={shippingForm.postal_code}
                    onChange={(event) =>
                      setShippingForm((current) => ({
                        ...current,
                        postal_code: event.target.value,
                      }))
                    }
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                    required
                  />
                </label>
                <label className="grid gap-2 md:col-span-2">
                  <span className="text-sm font-semibold text-burgundy-800">Teléfono</span>
                  <input
                    value={shippingForm.phone}
                    onChange={(event) =>
                      setShippingForm((current) => ({ ...current, phone: event.target.value }))
                    }
                    className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3"
                    required
                  />
                </label>
              </div>

              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.2em] text-burgundy-500">
                  Método de entrega
                </p>
                <div className="mt-4 grid gap-4">
                  {shippingQuoteQuery.isLoading ? (
                    <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 px-5 py-4 text-sm text-burgundy-700">
                      Calculando opciones de envío con la dirección cargada...
                    </div>
                  ) : null}

                  {!shippingQuoteQuery.isLoading && shippingQuoteError ? (
                    <div className="rounded-[24px] border border-burgundy-200 bg-burgundy-50 px-5 py-4 text-sm text-burgundy-800">
                      {shippingQuoteError}
                    </div>
                  ) : null}

                  {!shippingQuoteQuery.isLoading &&
                  !shippingQuoteError &&
                  shippingOptions.length === 0 ? (
                    <div className="rounded-[24px] border border-burgundy-100 bg-cream-50 px-5 py-4 text-sm text-burgundy-700">
                      Completá ciudad, provincia y código postal para cotizar el envío.
                    </div>
                  ) : null}

                  {shippingOptions.map((option) => (
                    <label
                      key={option.shipping_method}
                      className={`rounded-[24px] border px-5 py-4 ${
                        shippingForm.shipping_method === option.shipping_method
                          ? "border-burgundy-300 bg-burgundy-50"
                          : "border-burgundy-100 bg-cream-50"
                      }`}
                    >
                      <div className="flex items-start gap-4">
                        <input
                          type="radio"
                          name="shipping_method"
                          value={option.shipping_method}
                          checked={shippingForm.shipping_method === option.shipping_method}
                          onChange={() =>
                            setShippingForm((current) => ({
                              ...current,
                              shipping_method: option.shipping_method,
                            }))
                          }
                        />
                        <div className="flex-1">
                          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                            <p className="font-semibold text-burgundy-950">{option.label}</p>
                            <p className="text-sm font-semibold text-burgundy-900">
                              {Number.parseFloat(option.shipping_cost) > 0
                                ? formatARS(option.shipping_cost)
                                : "Sin cargo"}
                            </p>
                          </div>
                          <p className="mt-2 text-sm leading-6 text-burgundy-700">
                            {option.description}
                          </p>
                          {option.estimated_delivery ? (
                            <p className="mt-2 text-xs font-semibold uppercase tracking-[0.18em] text-burgundy-500">
                              Estimado: {formatDate(option.estimated_delivery)}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              <label className="grid gap-2">
                <span className="text-sm font-semibold text-burgundy-800">Notas del pedido</span>
                <textarea
                  value={shippingForm.notes}
                  onChange={(event) =>
                    setShippingForm((current) => ({ ...current, notes: event.target.value }))
                  }
                  className="min-h-28 rounded-[24px] border border-burgundy-200 bg-cream-50 px-4 py-3"
                  placeholder="Indicaciones de entrega, regalo o coordinación especial."
                />
              </label>

              {paymentError ? (
                <div className="rounded-[22px] border border-burgundy-200 bg-burgundy-50 px-4 py-3 text-sm text-burgundy-800">
                  {paymentError}
                  {createdOrder ? (
                    <>
                      {" "}
                      La orden ya fue creada y podés retomarla desde{" "}
                      <Link to={`/pedidos/${createdOrder.id}`} className="font-semibold underline">
                        este detalle
                      </Link>
                      .
                    </>
                  ) : null}
                </div>
              ) : null}

              <Button
                className="w-full"
                type="submit"
                disabled={
                  checkoutMutation.isPending ||
                  shippingQuoteQuery.isLoading ||
                  Boolean(shippingQuoteError) ||
                  !selectedShipping
                }
              >
                {checkoutMutation.isPending
                  ? "Generando orden y preparando pago..."
                  : shippingQuoteQuery.isLoading
                    ? "Cotizando envío..."
                    : "Confirmar pedido y pagar con Mercado Pago"}
              </Button>
            </form>
          )}
        </div>

        <aside className="space-y-5">
          <div className="rounded-[32px] border border-burgundy-100 bg-white p-6 shadow-velvet">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-burgundy-500">
              Resumen del pedido
            </p>
            <div className="mt-5 space-y-4">
              {items.map((item) => (
                <div
                  key={item.wineId}
                  className="flex items-start gap-4 rounded-[22px] border border-burgundy-100 bg-cream-50 p-4"
                >
                  <img
                    src={wineImageSrc(item.primaryImage)}
                    alt={item.name}
                    onError={applyWineImageFallback}
                    className="h-20 w-16 rounded-[16px] object-cover"
                  />
                  <div className="flex-1">
                    <p className="font-semibold text-burgundy-950">{item.name}</p>
                    <p className="mt-1 text-sm text-burgundy-700">
                      {item.varietalName} · {item.vintageYear}
                    </p>
                    <div className="mt-2 flex items-center justify-between text-sm text-burgundy-800">
                      <span>{item.quantity} botella(s)</span>
                      <span>{formatARS(Number.parseFloat(item.price) * item.quantity)}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 space-y-3 border-t border-burgundy-100 pt-5 text-sm text-burgundy-800">
              <div className="flex items-center justify-between">
                <span>Subtotal</span>
                <span>{subtotalFormatted}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>{selectedShipping?.label ?? "Envío"}</span>
                <span>
                  {selectedShipping
                    ? shippingCost > 0
                      ? formatARS(selectedShipping.shipping_cost)
                      : "Sin cargo"
                    : "Calculando..."}
                </span>
              </div>
              <div className="flex items-center justify-between text-lg font-semibold text-burgundy-950">
                <span>Total</span>
                <span>{formatARS(total)}</span>
              </div>
            </div>
          </div>

          <div className="rounded-[32px] border border-white/70 bg-burgundy-950 p-6 text-cream-50 shadow-velvet">
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-gold-300">
              Qué pasa ahora
            </p>
            <div className="mt-5 space-y-3 text-sm leading-6 text-cream-100/80">
              <p>1. Creamos la orden en el backend con sus ítems, totales y dirección.</p>
              <p>2. Generamos la preferencia de Checkout Pro en Mercado Pago.</p>
              <p>3. Mercado Pago procesa el cobro y nos notifica vía webhook.</p>
              <p>4. El pedido queda disponible en tu historial con su estado real.</p>
            </div>
          </div>
        </aside>
      </div>
    </section>
  );
}
