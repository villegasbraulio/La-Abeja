import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { ScrollToTop } from "./components/layout/ScrollToTop";
import { ToastViewport } from "./components/ui/ToastViewport";
import { AboutPage } from "./pages/About";
import { BackofficeApprovalsPage } from "./pages/Backoffice/ApprovalsPage";
import { BackofficeLayout } from "./pages/Backoffice/BackofficeLayout";
import { BackofficeCancellationApprovalsPage } from "./pages/Backoffice/CancellationApprovalsPage";
import { CategoriesPage } from "./pages/Backoffice/CategoriesPage";
import { BackofficeCopilotPage } from "./pages/Backoffice/CopilotPage";
import { BackofficeDashboardPage } from "./pages/Backoffice/DashboardPage";
import { BackofficeLoginPage } from "./pages/Backoffice/LoginPage";
import { BackofficeOrdersPage } from "./pages/Backoffice/OrdersPage";
import { BackofficeSalesMetricsPage } from "./pages/Backoffice/SalesMetricsPage";
import { BackofficeStockReservationsPage } from "./pages/Backoffice/StockReservationsPage";
import { BackofficeTasksPage } from "./pages/Backoffice/TasksPage";
import { BackofficeVisitsPage } from "./pages/Backoffice/VisitsPage";
import { VarietalsPage } from "./pages/Backoffice/VarietalsPage";
import { WinesPage } from "./pages/Backoffice/WinesPage";
import { CartPage } from "./pages/Cart";
import { CatalogPage } from "./pages/Catalog";
import { CheckoutPage } from "./pages/Checkout";
import { CheckoutResultPage } from "./pages/CheckoutResult";
import { ContactPage } from "./pages/Contact";
import { GiftsPage } from "./pages/Gifts";
import { GuidePage } from "./pages/Guide";
import { LandingPage } from "./pages/Landing";
import { OrderDetailPage } from "./pages/OrderDetail";
import { OrdersPage } from "./pages/Orders";
import { ProductDetailPage } from "./pages/ProductDetail";
import { VisitPage } from "./pages/Visit";
import { VisitBookingResultPage } from "./pages/Visit/ResultPage";

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/vinos" element={<CatalogPage />} />
          <Route path="/vinos/:slug" element={<ProductDetailPage />} />
          <Route path="/visitas" element={<VisitPage />} />
          <Route path="/visitas/horarios" element={<VisitPage />} />
          <Route path="/visitas/pago" element={<VisitPage />} />
          <Route path="/visitas/resultado" element={<VisitBookingResultPage />} />
          <Route path="/historia" element={<AboutPage />} />
          <Route path="/regalos" element={<GiftsPage />} />
          <Route path="/guia-de-compra" element={<GuidePage />} />
          <Route path="/contacto" element={<ContactPage />} />
          <Route path="/carrito" element={<CartPage />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/checkout/resultado" element={<CheckoutResultPage />} />
          <Route path="/pedidos" element={<OrdersPage />} />
          <Route path="/pedidos/:id" element={<OrderDetailPage />} />
        </Route>
        <Route path="/backoffice/login" element={<BackofficeLoginPage />} />
        <Route path="/backoffice" element={<BackofficeLayout />}>
          <Route index element={<BackofficeDashboardPage />} />
          <Route path="copilot" element={<BackofficeCopilotPage />} />
          <Route path="metricas" element={<BackofficeSalesMetricsPage />} />
          <Route path="tareas" element={<BackofficeTasksPage />} />
          <Route path="aprobaciones" element={<BackofficeApprovalsPage />} />
          <Route path="reservas-stock" element={<BackofficeStockReservationsPage />} />
          <Route path="cancelaciones" element={<BackofficeCancellationApprovalsPage />} />
          <Route path="visitas" element={<BackofficeVisitsPage />} />
          <Route path="pedidos" element={<BackofficeOrdersPage />} />
          <Route path="vinos" element={<WinesPage />} />
          <Route path="categorias" element={<CategoriesPage />} />
          <Route path="varietales" element={<VarietalsPage />} />
        </Route>
      </Routes>
      <ToastViewport />
    </>
  );
}
