import { Link, NavLink, Outlet, Navigate, useNavigate } from "react-router";
import {
  ArrowUpRight,
  Aperture,
  LayoutGrid,
  ChartNoAxesCombined,
  Settings,
  LogOut,
  ShieldCheck,
} from "lucide-react";
import { useSession } from "../../features/auth/use-session";
import { Button } from "../ui/button";
import { Loading, ErrorState } from "../feedback/states";
import { write } from "../../lib/api-client";
import { Onboarding, ThemeSync } from "../../features/settings/preferences";
import { queryClient } from "../../app/providers";
export function Logo() {
  return (
    <Link to="/" className="logo" aria-label="WorkQuest home">
      <span className="logo-mark">
        <Aperture size={23} strokeWidth={2.5} />
      </span>
      workquest<span className="logo-period">.</span>
    </Link>
  );
}
export function PublicHeader() {
  return (
    <header className="public-header">
      <Logo />
      <nav aria-label="Public navigation">
        <a href="/#how-it-works" className="text-link">
          How it works
        </a>
        <Link className="text-link" to="/sign-in">
          Sign in
        </Link>
        <Button asChild size="small">
          <Link to="/missions">
            Start a mission <ArrowUpRight size={16} />
          </Link>
        </Button>
      </nav>
    </header>
  );
}
export function ProtectedShell() {
  const session = useSession();
  const nav = useNavigate();
  if (session.isPending) return <Loading />;
  if (session.error)
    return (
      <ErrorState error={session.error} retry={() => void session.refetch()} />
    );
  if (!session.data) return <Navigate to="/sign-in" replace />;
  const user = session.data;
  return (
    <div className="app-shell">
      <aside className="sidebar glass">
        <Logo />
        <span className="eyebrow sidebar-label">YOUR PRACTICE SPACE</span>
        <nav aria-label="Main navigation">
          <NavLink to="/missions">
            <LayoutGrid size={20} /> Missions
          </NavLink>
          <NavLink to="/progress">
            <ChartNoAxesCombined size={20} /> Progress
          </NavLink>
          <NavLink to="/settings">
            <Settings size={20} /> Settings
          </NavLink>
          {user.role === "admin" && (
            <NavLink to="/admin/scenarios">
              <ShieldCheck size={20} /> Administration
            </NavLink>
          )}
        </nav>
        <div className="sidebar-bottom">
          <div className="avatar">{user.display_name.slice(0, 1)}</div>
          <div>
            <strong>{user.display_name}</strong>
            <small>
              {user.is_demo
                ? "Demo · expires in two hours"
                : "Your next chapter starts here"}
            </small>
          </div>
          <button
            className="icon-button"
            aria-label="Sign out"
            onClick={() =>
              void write("/auth/logout").then(() => {
                for (const key of Object.keys(sessionStorage))
                  if (key.startsWith("wq:")) sessionStorage.removeItem(key);
                queryClient.clear();
                nav("/");
              })
            }
          >
            <LogOut size={18} />
          </button>
        </div>
      </aside>
      <main id="main" className="app-main">
        <ThemeSync />
        <Onboarding />
        {user.is_demo && (
          <div className="mode-banner">
            DEMO · Isolated practice · Mock teammates · No public sharing
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
