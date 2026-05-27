import { useMemo } from "react";
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { authApi } from "../../api/auth";
import { useAuthStore } from "../../store/authStore";
import { cn } from "../../lib/utils";

const backofficeLinks = [
  { label: "Resumen", href: "/backoffice" },
  { label: "Copilot", href: "/backoffice/copilot" },
  { label: "Vinos", href: "/backoffice/vinos" },
  { label: "Categorias", href: "/backoffice/categorias" },
  { label: "Varietales", href: "/backoffice/varietales" },
];

export function BackofficeLayout() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const location = useLocation();

  const pageTitle = useMemo(() => {
    const currentSection = backofficeLinks.find((link) => location.pathname === link.href);
    return currentSection?.label ?? "Backoffice";
  }, [location.pathname]);

  if (!accessToken || !user) {
    return <Navigate to="/backoffice/login" replace />;
  }

  if (!user.is_staff) {
    return <Navigate to="/" replace />;
  }

  async function handleLogout() {
    try {
      if (refreshToken) {
        await authApi.logout(refreshToken);
      }
    } catch {
      // Ignore logout API errors and clear local state anyway.
    } finally {
      logout();
      navigate("/backoffice/login");
    }
  }

  return (
    <div className="min-h-screen bg-[#f6f1ea] text-burgundy-950">
      <div className="grid min-h-screen lg:grid-cols-[280px_1fr]">
        <aside className="border-r border-burgundy-100 bg-burgundy-950 px-6 py-8 text-cream-50">
          <Link to="/backoffice" className="block">
            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gold-300">
              Backoffice
            </p>
            <h1 className="mt-3 font-serif text-4xl">Bodega La Abeja</h1>
            <p className="mt-3 leading-7 text-cream-100/75">
              Gestion interna para catalogo, precios, stock e imagenes sin depender del admin de Django.
            </p>
          </Link>

          <nav className="mt-10 space-y-2">
            {backofficeLinks.map((link) => (
              <NavLink
                key={link.href}
                to={link.href}
                end={link.href === "/backoffice"}
                className={({ isActive }) =>
                  cn(
                    "block rounded-[20px] px-4 py-3 text-sm font-semibold transition-colors",
                    isActive
                      ? "bg-white text-burgundy-950"
                      : "text-cream-100/80 hover:bg-white/10 hover:text-white",
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>

          <div className="mt-10 rounded-[24px] border border-white/10 bg-white/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
              Sesion
            </p>
            <p className="mt-3 text-lg font-semibold">{user.full_name || user.email}</p>
            <p className="mt-1 text-sm text-cream-100/70">{user.email}</p>
          </div>

          <div className="mt-6 flex flex-col gap-3">
            <Link to="/" className="inline-flex">
              <Button variant="ghost" className="w-full border-white/20 text-cream-50 hover:bg-white/10">
                Ver storefront
              </Button>
            </Link>
            <Button variant="secondary" onClick={handleLogout}>
              Cerrar sesion
            </Button>
          </div>
        </aside>

        <div className="flex min-h-screen flex-col">
          <header className="border-b border-burgundy-100 bg-white/80 px-6 py-5 backdrop-blur-xl md:px-8">
            <p className="text-sm font-semibold uppercase tracking-[0.24em] text-burgundy-500">
              Operaciones internas
            </p>
            <h2 className="mt-2 font-serif text-4xl text-burgundy-950">{pageTitle}</h2>
          </header>
          <div className="flex-1 px-6 py-8 md:px-8">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
}
