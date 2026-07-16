import { Outlet } from "react-router-dom";
import Navbar from "../components/Navbar.jsx";

function MainLayout() {
  return (
    <div className="app-shell">
      <Navbar />
      <main className="page-shell">
        <Outlet />
      </main>
    </div>
  );
}

export default MainLayout;
