import { Link, Outlet } from "react-router";

import { useAuth, useCurrentUser } from "../features/auth/authContext";
import { NotificationBell } from "../features/notifications/NotificationBell";
import { Button } from "./Button";

/** The frame of every logged-in page: app name, notifications, user and logout. */
export function AppLayout() {
  const { logout } = useAuth();
  const user = useCurrentUser();
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between gap-3 px-4 py-2">
          <Link to="/" className="font-semibold text-slate-900">
            Task manager
          </Link>
          <div className="flex min-w-0 items-center gap-2">
            <NotificationBell />
            <span className="hidden truncate text-sm text-slate-600 sm:inline" title={user.email}>
              {user.email}
              {user.is_admin && " (admin)"}
            </span>
            <Button variant="ghost" onClick={() => void logout()}>
              Log out
            </Button>
          </div>
        </div>
      </header>
      <Outlet />
    </div>
  );
}
