import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Navbar } from "../../src/components/layout/Navbar";
import { useAuthStore } from "../../src/store/authStore";
import { useCartStore } from "../../src/store/cartStore";

function renderNavbar() {
  return render(
    <MemoryRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Navbar />
    </MemoryRouter>,
  );
}

describe("Navbar", () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      user: null,
    });
    useCartStore.setState({ items: [] });
  });

  it("opens the mobile menu as an overlay panel", async () => {
    const user = userEvent.setup();
    renderNavbar();

    await user.click(screen.getByRole("button", { name: /abrir navegación/i }));

    expect(screen.getByText(/comprar o reservar/i)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /vinos/i }).length).toBeGreaterThanOrEqual(2);
  });

  it("opens a side drawer preview when the cart button is pressed", async () => {
    const user = userEvent.setup();

    useCartStore.setState({
      items: [
        {
          wineId: "wine-1",
          slug: "gran-malbec-reserva",
          name: "Gran Malbec Reserva",
          price: "18500.00",
          primaryImage: null,
          varietalName: "Malbec",
          vintageYear: 2022,
          quantity: 2,
        },
      ],
    });

    renderNavbar();

    await user.click(screen.getByTestId("cart-count"));

    expect(screen.getByLabelText(/vista previa del carrito/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ir al carrito/i })).toBeInTheDocument();
    expect(screen.getByText(/gran malbec reserva/i)).toBeInTheDocument();
  });
});
