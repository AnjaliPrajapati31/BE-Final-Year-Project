import { NavLink } from "react-router-dom";

const linkClass = ({ isActive }) =>
  isActive ? "nav-link nav-link-active" : "nav-link";

function Navbar() {
  return (
    <header className="topbar">
      <div className="brand">AI Agriculture</div>
      <nav className="nav">
        <NavLink to="/" className={linkClass} end>
          Home
        </NavLink>
      </nav>
    </header>
  );
}

export default Navbar;
