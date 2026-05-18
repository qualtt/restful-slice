import type { PropsWithChildren } from "react";
import { Link, NavLink } from "react-router-dom";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <div className="mx-auto flex min-h-screen max-w-5xl flex-col p-2">
      <header className="mb-4 flex items-center justify-between window-2002 p-2">
        <div className="flex items-center gap-4">
          <Link to="/" className="text-xl font-bold text-black no-underline">
            Restful Slice
          </Link>
        </div>
        <nav className="flex gap-4 text-sm">
          <NavLink to="/" className={({ isActive }) => (isActive ? "text-black font-bold" : "text-blue-700 underline hover:text-blue-800")}>
            Dashboard
          </NavLink>
        </nav>
      </header>
      <main className="flex-1">{children}</main>
      <footer className="mt-8 text-center text-xs text-gray-600 border-t border-gray-400 pt-2">
        <p>&copy; 2002 Restful Slice. Operator sessions are key-scoped.</p>
      </footer>
    </div>
  );
}
