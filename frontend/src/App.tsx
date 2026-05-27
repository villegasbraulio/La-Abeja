import { Route, Routes } from "react-router-dom";
import { Layout } from "./components/layout/Layout";
import { AboutPage } from "./pages/About";
import { BackofficeLayout } from "./pages/Backoffice/BackofficeLayout";
import { CategoriesPage } from "./pages/Backoffice/CategoriesPage";
import { BackofficeCopilotPage } from "./pages/Backoffice/CopilotPage";
import { BackofficeDashboardPage } from "./pages/Backoffice/DashboardPage";
import { BackofficeLoginPage } from "./pages/Backoffice/LoginPage";
import { VarietalsPage } from "./pages/Backoffice/VarietalsPage";
import { WinesPage } from "./pages/Backoffice/WinesPage";
import { CartPage } from "./pages/Cart";
import { CatalogPage } from "./pages/Catalog";
import { ContactPage } from "./pages/Contact";
import { GiftsPage } from "./pages/Gifts";
import { GuidePage } from "./pages/Guide";
import { LandingPage } from "./pages/Landing";
import { ProductDetailPage } from "./pages/ProductDetail";
import { VisitPage } from "./pages/Visit";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/vinos" element={<CatalogPage />} />
        <Route path="/vinos/:slug" element={<ProductDetailPage />} />
        <Route path="/visitas" element={<VisitPage />} />
        <Route path="/historia" element={<AboutPage />} />
        <Route path="/regalos" element={<GiftsPage />} />
        <Route path="/guia-de-compra" element={<GuidePage />} />
        <Route path="/contacto" element={<ContactPage />} />
        <Route path="/carrito" element={<CartPage />} />
      </Route>
      <Route path="/backoffice/login" element={<BackofficeLoginPage />} />
      <Route path="/backoffice" element={<BackofficeLayout />}>
        <Route index element={<BackofficeDashboardPage />} />
        <Route path="copilot" element={<BackofficeCopilotPage />} />
        <Route path="vinos" element={<WinesPage />} />
        <Route path="categorias" element={<CategoriesPage />} />
        <Route path="varietales" element={<VarietalsPage />} />
      </Route>
    </Routes>
  );
}
