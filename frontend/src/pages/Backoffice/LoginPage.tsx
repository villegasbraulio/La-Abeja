import { type FormEvent, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { AxiosError } from "axios";
import { Button } from "../../components/ui/Button";
import { authApi } from "../../api/auth";
import { useAuthStore } from "../../store/authStore";

export function BackofficeLoginPage() {
  const navigate = useNavigate();
  const accessToken = useAuthStore((state) => state.accessToken);
  const user = useAuthStore((state) => state.user);
  const setSession = useAuthStore((state) => state.setSession);
  const [email, setEmail] = useState("admin@bodegalaabeja.com.ar");
  const [password, setPassword] = useState("LaAbejaAdmin2026!");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (accessToken && user?.is_staff) {
    return <Navigate to="/backoffice" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const session = await authApi.login({ email, password });
      if (!session.user.is_staff) {
        setErrorMessage("Tu usuario existe, pero no tiene permisos para entrar al backoffice.");
        return;
      }
      setSession({
        accessToken: session.access,
        refreshToken: session.refresh,
        user: session.user,
      });
      navigate("/backoffice");
    } catch (error) {
      const axiosError = error as AxiosError<{ detail?: string }>;
      setErrorMessage(
        axiosError.response?.data?.detail ??
          "No pudimos iniciar sesion. Revisá el email y la contraseña.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(200,169,110,0.12),transparent_28%),linear-gradient(180deg,#faf7f2,#f2e8da)] px-6 py-16">
      <div className="mx-auto grid max-w-6xl gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div className="rounded-[36px] border border-white/70 bg-burgundy-950 p-8 text-cream-50 shadow-velvet md:p-10">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-gold-300">
            Panel interno
          </p>
          <h1 className="mt-4 font-serif text-5xl text-white">
            Backoffice custom para operar la bodega sin tocar Django admin.
          </h1>
          <p className="mt-5 max-w-xl leading-8 text-cream-100/80">
            Diseñado para equipos de empresa: catálogo, precios, stock e imágenes con una
            experiencia más clara, comercial y orientada a operación.
          </p>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {[
              "Editar vinos y fotos",
              "Controlar stock y destacados",
              "Mantener categorías y varietales",
            ].map((item) => (
              <div key={item} className="rounded-[24px] border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-sm leading-6 text-cream-100/80">{item}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-[36px] border border-burgundy-100 bg-white p-8 shadow-velvet md:p-10">
          <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
            Iniciar sesión
          </p>
          <h2 className="mt-3 font-serif text-4xl text-burgundy-950">Entrar al backoffice</h2>
          <p className="mt-4 text-burgundy-700">
            Usá un usuario staff para entrar al panel de gestión interna.
          </p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Email</span>
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                required
              />
            </label>

            <label className="grid gap-2">
              <span className="text-sm font-semibold text-burgundy-800">Contraseña</span>
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="rounded-2xl border border-burgundy-200 bg-cream-50 px-4 py-3 text-burgundy-950 outline-none focus:border-burgundy-400"
                required
              />
            </label>

            {errorMessage ? (
              <div className="rounded-[20px] border border-burgundy-200 bg-burgundy-50 px-4 py-3 text-sm text-burgundy-800">
                {errorMessage}
              </div>
            ) : null}

            <Button className="w-full" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Ingresando..." : "Entrar al backoffice"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
