import {
  BookOpen,
  ChevronRight,
  Gift,
  House,
  Landmark,
  Mail,
  MapPinned,
  Menu,
  ShoppingBag,
  Wine,
  X,
} from "lucide-react";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { CartDrawer } from "./CartDrawer";
import { siteLinks } from "../../lib/constants";
import { useCart } from "../../hooks/useCart";
import { useAuthStore } from "../../store/authStore";
import { cn } from "../../lib/utils";

const mobileLinkIcons = {
  "/": House,
  "/vinos": Wine,
  "/visitas": MapPinned,
  "/historia": Landmark,
  "/regalos": Gift,
  "/guia-de-compra": BookOpen,
  "/contacto": Mail,
} as const;

export function Navbar() {
  const { itemCount } = useCart();
  const user = useAuthStore((state) => state.user);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setIsMenuOpen(false);
    setIsCartOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!isMenuOpen && !isCartOpen) {
      document.body.style.overflow = "";
      return;
    }

    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = "";
    };
  }, [isCartOpen, isMenuOpen]);

  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsMenuOpen(false);
        setIsCartOpen(false);
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, []);

  return (
    <>
      <header className="relative sticky top-0 z-50 border-b border-white/50 bg-cream-50/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
          <div className="flex items-center gap-4">
            <button
              type="button"
              className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-burgundy-200 bg-white text-burgundy-900 transition-colors duration-300 hover:bg-burgundy-50 md:hidden"
              onClick={() => setIsMenuOpen((current) => !current)}
              aria-expanded={isMenuOpen}
              aria-label={isMenuOpen ? "Cerrar navegacion" : "Abrir navegacion"}
            >
              {isMenuOpen ? <X className="h-5 w-5" strokeWidth={1.9} /> : <Menu className="h-5 w-5" strokeWidth={1.9} />}
            </button>
            <Link to="/" className="font-serif text-2xl text-burgundy-900 md:text-3xl">
              Bodega La Abeja
            </Link>
          </div>

          <nav className="hidden items-center gap-6 md:flex xl:gap-8">
            {siteLinks.map((link) => (
              <NavLink
                key={link.href}
                to={link.href}
                className="relative"
              >
                {({ isActive }) => (
                  <motion.span
                    whileTap={{ scale: 0.96 }}
                    className={cn(
                      "relative inline-flex px-1 py-2 text-xs font-semibold uppercase tracking-[0.2em] transition-colors duration-300",
                      isActive ? "text-burgundy-950" : "text-burgundy-700",
                    )}
                  >
                    {link.label}
                    {isActive ? (
                      <motion.span
                        layoutId="site-nav-underline"
                        className="absolute inset-x-0 -bottom-0.5 h-0.5 rounded-full bg-burgundy-900"
                        transition={{ type: "spring", stiffness: 380, damping: 30 }}
                      />
                    ) : null}
                  </motion.span>
                )}
              </NavLink>
            ))}
          </nav>

          <div className="hidden items-center gap-3 xl:flex">
            {user ? (
              <Link
                to="/pedidos"
                className="rounded-full border border-burgundy-200 bg-white px-4 py-2 text-sm font-semibold text-burgundy-900"
              >
                Mis pedidos
              </Link>
            ) : null}
            {user?.is_staff ? (
              <Link
                to="/backoffice"
                className="rounded-full border border-burgundy-900 bg-burgundy-900 px-4 py-2 text-sm font-semibold text-gold-300"
              >
                Backoffice
              </Link>
            ) : null}
            <p className="text-right text-xs uppercase tracking-[0.18em] text-burgundy-600">
              San Rafael
              <span className="block pt-1 text-[11px] tracking-[0.16em] text-burgundy-400">
                Compras, visitas y concierge
              </span>
            </p>
          </div>

          <button
            type="button"
            onClick={() => {
              setIsMenuOpen(false);
              setIsCartOpen(true);
            }}
            aria-label={`Abrir carrito con ${itemCount} ${itemCount === 1 ? "vino" : "vinos"}`}
            className="group inline-flex items-center gap-3 rounded-full border border-burgundy-900 bg-burgundy-900 px-3 py-2 text-left text-cream-50 shadow-[0_18px_40px_-24px_rgba(79,18,31,0.85)] transition-all duration-300 hover:-translate-y-0.5 hover:bg-burgundy-800"
            data-testid="cart-count"
          >
            <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-gold-300 transition-transform duration-300 group-hover:scale-105">
              <ShoppingBag className="h-5 w-5" strokeWidth={1.9} />
            </span>
            <span className="hidden flex-col sm:flex">
              <span className="text-[10px] font-semibold uppercase tracking-[0.24em] text-gold-300/80">
                Carrito
              </span>
              <span className="pt-1 text-sm font-semibold text-white">
                {itemCount === 0 ? "Sin vinos" : `${itemCount} ${itemCount === 1 ? "vino" : "vinos"}`}
              </span>
            </span>
            <span className="inline-flex min-w-[2rem] items-center justify-center rounded-full bg-gold-300 px-2 py-1 text-sm font-bold text-burgundy-950">
              {itemCount}
            </span>
          </button>
        </div>

        <button
          type="button"
          aria-label="Cerrar menu"
          onClick={() => setIsMenuOpen(false)}
          className={cn(
            "fixed inset-0 z-40 bg-burgundy-950/20 backdrop-blur-[2px] transition-opacity duration-300 md:hidden",
            isMenuOpen ? "opacity-100" : "pointer-events-none opacity-0",
          )}
        />

        <div
          className={cn(
            "absolute inset-x-4 top-[calc(100%+0.75rem)] z-50 origin-top rounded-[32px] border border-white/70 bg-[linear-gradient(180deg,rgba(255,249,242,0.97)_0%,rgba(248,241,232,0.98)_100%)] p-5 shadow-[0_28px_70px_-35px_rgba(79,18,31,0.45)] transition-all duration-300 ease-out md:hidden",
            isMenuOpen
              ? "visible translate-y-0 scale-100 opacity-100"
              : "invisible -translate-y-3 scale-[0.98] opacity-0",
          )}
        >
          <div className="mb-4 flex items-start justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-burgundy-500">
                Navegacion
              </p>
              <p className="mt-2 font-serif text-2xl text-burgundy-950">Explora la bodega</p>
            </div>
            <button
              type="button"
              onClick={() => setIsMenuOpen(false)}
              aria-label="Cerrar navegacion"
              className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-burgundy-100 bg-white/80 text-burgundy-900 transition-colors duration-300 hover:bg-white"
            >
              <X className="h-5 w-5" strokeWidth={1.9} />
            </button>
          </div>

          <nav className="flex flex-col gap-3">
            {siteLinks.map((link) => {
              const Icon = mobileLinkIcons[link.href as keyof typeof mobileLinkIcons] ?? House;

              return (
                <NavLink
                  key={link.href}
                  to={link.href}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center justify-between rounded-[24px] border border-transparent bg-white/75 px-4 py-4 text-sm font-semibold text-burgundy-800 transition-all duration-300",
                      isActive && "border-burgundy-200 bg-white text-burgundy-950 shadow-velvet",
                    )
                  }
                >
                  {({ isActive }) => (
                    <motion.div
                      whileTap={{ scale: 0.98 }}
                      className="flex w-full items-center justify-between"
                    >
                      <span className="flex items-center gap-3">
                        <motion.span
                          animate={isActive ? { scale: 1.06 } : { scale: 1 }}
                          transition={{ type: "spring", stiffness: 320, damping: 22 }}
                          className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-burgundy-50 text-burgundy-900"
                        >
                          <Icon className="h-5 w-5" strokeWidth={1.8} />
                        </motion.span>
                        {link.label}
                      </span>
                      <motion.span
                        animate={isActive ? { x: 2 } : { x: 0 }}
                        transition={{ type: "spring", stiffness: 320, damping: 22 }}
                      >
                        <ChevronRight className="h-4 w-4 text-burgundy-400" strokeWidth={1.8} />
                      </motion.span>
                    </motion.div>
                  )}
                </NavLink>
              );
            })}
            {user ? (
              <NavLink
                to="/pedidos"
                className={({ isActive }) =>
                  cn(
                    "flex items-center justify-between rounded-[24px] border border-transparent bg-white/75 px-4 py-4 text-sm font-semibold text-burgundy-800 transition-all duration-300",
                    isActive && "border-burgundy-200 bg-white text-burgundy-950 shadow-velvet",
                  )
                }
              >
                <span className="flex items-center gap-3">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-burgundy-50 text-burgundy-900">
                    <ShoppingBag className="h-5 w-5" strokeWidth={1.8} />
                  </span>
                  Mis pedidos
                </span>
                <ChevronRight className="h-4 w-4 text-burgundy-400" strokeWidth={1.8} />
              </NavLink>
            ) : null}
            {user?.is_staff ? (
              <NavLink
                to="/backoffice"
                className={({ isActive }) =>
                  cn(
                    "flex items-center justify-between rounded-[24px] border border-transparent bg-burgundy-900 px-4 py-4 text-sm font-semibold text-gold-300 transition-all duration-300",
                    isActive && "shadow-velvet",
                  )
                }
              >
                <span className="flex items-center gap-3">
                  <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-gold-300">
                    <Landmark className="h-5 w-5" strokeWidth={1.8} />
                  </span>
                  Backoffice
                </span>
                <span className="text-gold-300/70">Admin</span>
              </NavLink>
            ) : null}
          </nav>

          <div className="mt-4 rounded-[24px] bg-burgundy-950 px-5 py-5 text-cream-50">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-gold-300/80">
              Concierge
            </p>
            <p className="mt-3 text-sm leading-6 text-cream-100/80">
              Compras, visitas y regalos con atencion cercana desde cualquier dispositivo.
            </p>
          </div>
        </div>
      </header>

      <CartDrawer isOpen={isCartOpen} onClose={() => setIsCartOpen(false)} />
    </>
  );
}
