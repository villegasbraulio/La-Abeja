import { Outlet } from "react-router-dom";
import { Footer } from "./Footer";
import { Navbar } from "./Navbar";

export function Layout() {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(200,169,110,0.10),transparent_28%),radial-gradient(circle_at_bottom_right,rgba(114,47,55,0.08),transparent_24%),#faf7f2]">
      <Navbar />
      <main className="overflow-x-hidden">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
