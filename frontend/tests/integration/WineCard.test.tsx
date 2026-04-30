import type { ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { WineCard } from "../../src/components/wine/WineCard";
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

describe("WineCard", () => {
  it("renders pricing and metadata", () => {
    renderWithProviders(<WineCard wine={buildWine()} />);

    expect(screen.getByText(/Gran Malbec Reserva/i)).toBeInTheDocument();
    expect(screen.getByText(/Malbec · 2022/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /agregar al carrito/i })).toBeEnabled();
  });

  it("disables add to cart when out of stock", async () => {
    const user = userEvent.setup();
    renderWithProviders(<WineCard wine={buildWine({ is_in_stock: false })} />);

    const button = screen.getByRole("button", { name: /agregar al carrito/i });
    await user.hover(button);

    expect(button).toBeDisabled();
    expect(screen.getByText(/Sin stock/i)).toBeInTheDocument();
  });
});
