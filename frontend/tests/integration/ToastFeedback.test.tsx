import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { ToastViewport } from "../../src/components/ui/ToastViewport";
import { WineCard } from "../../src/components/wine/WineCard";
import { useCartStore } from "../../src/store/cartStore";
import { useToastStore } from "../../src/store/toastStore";
import type { WineListItem } from "../../src/types/catalog";

function renderWithProviders(ui: ReactNode) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        future={{
          v7_startTransition: true,
          v7_relativeSplatPath: true,
        }}
      >
        {ui}
        <ToastViewport />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function buildWine(overrides: Partial<WineListItem> = {}): WineListItem {
  return {
    id: "wine-1",
    name: "Gran Malbec Reserva",
    slug: "gran-malbec-reserva",
    vintage_year: 2022,
    price: "18500.00",
    compare_at_price: "21000.00",
    discount_percentage: 12,
    varietal_name: "Malbec",
    category_name: "Vinos Tintos",
    primary_image: null,
    average_rating: 4.8,
    review_count: 24,
    is_in_stock: true,
    is_featured: true,
    is_limited_edition: false,
    alcohol_percentage: "14.2",
    ...overrides,
  };
}

describe("Toast feedback", () => {
  beforeEach(() => {
    localStorage.clear();
    useCartStore.setState({ items: [] });
    useToastStore.getState().clearToasts();
  });

  it("shows a success toast when a wine is added to the cart", async () => {
    const user = userEvent.setup();

    renderWithProviders(<WineCard wine={buildWine()} />);

    await user.click(screen.getByRole("button", { name: /agregar al carrito/i }));

    expect(screen.getByText(/vino agregado al carrito/i)).toBeInTheDocument();
    expect(
      screen.getByText(/gran malbec reserva ya está listo para comprar cuando quieras/i),
    ).toBeInTheDocument();
  });
});
