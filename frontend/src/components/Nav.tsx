import { NavLink } from "react-router-dom";
import { useAsync } from "../hooks/useAsync";
import { api } from "../api/client";

export function Nav() {
  const { data: system } = useAsync(() => api.system(), []);

  return (
    <nav className="nav">
      <div className="nav-inner">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          GRIDSTATE
        </div>
        <div className="nav-links">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Discoveries
          </NavLink>
          <NavLink to="/states" className={({ isActive }) => (isActive ? "active" : "")}>
            States
          </NavLink>
          <NavLink to="/system" className={({ isActive }) => (isActive ? "active" : "")}>
            System
          </NavLink>
        </div>
        {system && (
          <span className="mode-badge" data-mode={system.mode}>
            {system.mode} DATA
          </span>
        )}
      </div>
    </nav>
  );
}
