import {
  Ban,
  Bot,
  CalendarDays,
  ChartNoAxesColumn,
  CircleCheck,
  ExternalLink,
  Layers,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  PackageCheck,
  ShoppingBag,
  Tags,
  Wine,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Navigate, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Button } from "../../components/ui/Button";
import { authApi } from "../../api/auth";
import { useAuthStore } from "../../store/authStore";
import { cn } from "../../lib/utils";

const backofficeLinks = [
  { label: "Resumen", href: "/backoffice", icon: LayoutDashboard },
  { label: "Métricas", href: "/backoffice/metricas", icon: ChartNoAxesColumn },
  { label: "Copilot", href: "/backoffice/copilot", icon: Bot },
  { label: "Tareas", href: "/backoffice/tareas", icon: ListChecks },
  { label: "Aprobaciones", href: "/backoffice/aprobaciones", icon: CircleCheck },
  { label: "Reservas de stock", href: "/backoffice/reservas-stock", icon: PackageCheck },
  { label: "Cancelaciones", href: "/backoffice/cancelaciones", icon: Ban },
  { label: "Visitas", href: "/backoffice/visitas", icon: CalendarDays },
  { label: "Pedidos", href: "/backoffice/pedidos", icon: ShoppingBag },
  { label: "Vinos", href: "/backoffice/vinos", icon: Wine },
  { label: "Categorias", href: "/backoffice/categorias", icon: Tags },
  { label: "Varietales", href: "/backoffice/varietales", icon: Layers },
];

export function BackofficeLayout() {
  const accessToken = useAuthStore((state) => state.accessToken);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const navigate = useNavigate();
  const location = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const pageTitle = useMemo(() => {
    const currentSection = backofficeLinks.find((link) => location.pathname === link.href);
    return currentSection?.label ?? "Backoffice";
  }, [location.pathname]);

  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isMenuOpen) {
      document.body.style.overflow = "";
      return;
    }

    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = "";
    };
  }, [isMenuOpen]);

  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsMenuOpen(false);
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, []);

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

  const renderNavigation = () => (
    <nav className="grid gap-1.5">
      {backofficeLinks.map((link) => {
        const Icon = link.icon;

        return (
          <NavLink
            key={link.href}
            to={link.href}
            end={link.href === "/backoffice"}
            className={({ isActive }) =>
              cn(
                "flex min-h-11 items-center gap-3 rounded-lg px-3 text-sm font-semibold transition-colors",
                isActive
                  ? "bg-white text-burgundy-950 shadow-[0_10px_28px_rgba(0,0,0,0.12)]"
                  : "text-cream-100/78 hover:bg-white/10 hover:text-white",
              )
            }
          >
            <Icon className="h-4 w-4 shrink-0" strokeWidth={1.9} />
            <span className="truncate">{link.label}</span>
          </NavLink>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen bg-[#f7f5f1] text-burgundy-950">
      <header className="sticky top-0 z-50 border-b border-burgundy-100 bg-[#fbfaf7]/95 px-4 py-3 backdrop-blur-xl lg:hidden">
        <div className="flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setIsMenuOpen(true)}
            aria-label="Abrir navegación del backoffice"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-burgundy-100 bg-white text-burgundy-950"
          >
            <Menu className="h-5 w-5" strokeWidth={1.9} />
          </button>
          <div className="min-w-0 text-center">
            <p className="truncate text-sm font-semibold text-burgundy-950">Bodega La Abeja</p>
            <p className="truncate text-xs text-burgundy-600">{pageTitle}</p>
          </div>
          <Link
            to="/"
            aria-label="Ver storefront"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-burgundy-100 bg-white text-burgundy-950"
          >
            <ExternalLink className="h-4 w-4" strokeWidth={1.9} />
          </Link>
        </div>
      </header>

      <button
        type="button"
        aria-label="Cerrar navegación"
        onClick={() => setIsMenuOpen(false)}
        className={cn(
          "fixed inset-0 z-50 bg-burgundy-950/35 backdrop-blur-sm transition-opacity lg:hidden",
          isMenuOpen ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[min(86vw,320px)] flex-col border-r border-white/10 bg-burgundy-950 px-4 py-4 text-cream-50 shadow-2xl transition-transform duration-300 lg:hidden",
          isMenuOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">Backoffice</p>
            <p className="mt-1 text-lg font-semibold">Bodega La Abeja</p>
          </div>
          <button
            type="button"
            onClick={() => setIsMenuOpen(false)}
            aria-label="Cerrar navegación del backoffice"
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg bg-white/10 text-white"
          >
            <X className="h-5 w-5" strokeWidth={1.9} />
          </button>
        </div>
        <div className="mt-4 flex-1 overflow-y-auto pr-1">{renderNavigation()}</div>
        <div className="mt-4 grid gap-2 border-t border-white/10 pt-4">
          <Link to="/">
            <Button variant="ghost" className="w-full border-white/20 bg-white/5 text-cream-50 hover:bg-white/10">
              <ExternalLink className="h-4 w-4" strokeWidth={1.9} />
              Storefront
            </Button>
          </Link>
          <Button variant="secondary" className="w-full" onClick={handleLogout}>
            <LogOut className="h-4 w-4" strokeWidth={1.9} />
            Salir
          </Button>
        </div>
      </aside>

      <div className="grid min-h-screen lg:grid-cols-[264px_minmax(0,1fr)]">
        <aside className="sticky top-0 hidden h-screen flex-col border-r border-white/10 bg-burgundy-950 px-4 py-5 text-cream-50 lg:flex">
          <Link to="/backoffice" className="rounded-lg px-2 py-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">Backoffice</p>
            <h1 className="mt-1.5 text-xl font-semibold">Bodega La Abeja</h1>
          </Link>

          <div className="mt-5 flex-1 overflow-y-auto pr-1">{renderNavigation()}</div>

          <div className="mt-5 rounded-lg border border-white/10 bg-white/5 p-3">
            <p className="truncate text-sm font-semibold">{user.full_name || user.email}</p>
            <p className="mt-1 truncate text-xs text-cream-100/65">{user.email}</p>
          </div>
        </aside>

        <div className="flex min-h-screen min-w-0 flex-col">
          <header className="sticky top-0 z-30 hidden border-b border-burgundy-100 bg-[#fbfaf7]/95 px-6 py-3 backdrop-blur-xl lg:block">
            <div className="mx-auto flex max-w-[1600px] items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-burgundy-500">
                  Operaciones
                </p>
                <h2 className="mt-1 truncate text-xl font-semibold text-burgundy-950">{pageTitle}</h2>
              </div>
              <div className="flex items-center gap-2">
                <Link to="/">
                  <Button variant="ghost" className="min-h-10 px-3 py-2">
                    <ExternalLink className="h-4 w-4" strokeWidth={1.9} />
                    Storefront
                  </Button>
                </Link>
                <Button variant="secondary" className="min-h-10 px-3 py-2" onClick={handleLogout}>
                  <LogOut className="h-4 w-4" strokeWidth={1.9} />
                  Salir
                </Button>
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-5 sm:px-6 lg:px-8 lg:py-6">
            <div className="mx-auto max-w-[1600px]">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
