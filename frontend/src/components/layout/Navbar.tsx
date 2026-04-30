import { useEffect, useState } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import { siteLinks } from "../../lib/constants";
import { useCart } from "../../hooks/useCart";
import { cn } from "../../lib/utils";

export function Navbar() {
  const { itemCount } = useCart();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    setIsMenuOpen(false);
  }, [location.pathname]);

  return (
    <header className="sticky top-0 z-50 border-b border-white/50 bg-cream-50/85 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
        <div className="flex items-center gap-4">
          <button
            type="button"
            className="inline-flex rounded-full border border-burgundy-200 bg-white px-3 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-burgundy-900 md:hidden"
            onClick={() => setIsMenuOpen((current) => !current)}
            aria-expanded={isMenuOpen}
            aria-label="Abrir navegacion"
          >
            Menu
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
              className={({ isActive }) =>
                cn(
                  "text-xs font-semibold tracking-[0.2em] text-burgundy-700 uppercase transition-colors",
                  isActive && "text-burgundy-950",
                )
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-3 xl:flex">
          <p className="text-right text-xs uppercase tracking-[0.18em] text-burgundy-600">
            San Rafael
            <span className="block pt-1 text-[11px] tracking-[0.16em] text-burgundy-400">
              Compras, visitas y concierge
            </span>
          </p>
        </div>

        <Link
          to="/carrito"
          className="rounded-full border border-burgundy-200 bg-white px-4 py-2 text-sm font-semibold text-burgundy-900"
          data-testid="cart-count"
        >
          Carrito {itemCount}
        </Link>
      </div>

      {isMenuOpen ? (
        <div className="border-t border-burgundy-100 bg-cream-50 px-6 py-5 md:hidden">
          <nav className="flex flex-col gap-4">
            {siteLinks.map((link) => (
              <NavLink
                key={link.href}
                to={link.href}
                className={({ isActive }) =>
                  cn(
                    "rounded-2xl border border-transparent bg-white/60 px-4 py-3 text-sm font-semibold text-burgundy-800",
                    isActive && "border-burgundy-200 bg-white text-burgundy-950",
                  )
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
      ) : null}
    </header>
  );
}
