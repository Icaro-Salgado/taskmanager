import { Navigate, Route, Routes, useLocation } from "react-router";

import { AppLayout } from "./components/AppLayout";
import { Loading } from "./components/Loading";
import { useAuth } from "./features/auth/authContext";
import { LoginPage } from "./features/auth/LoginPage";
import { ArchivedPage } from "./features/tasks/ArchivedPage";
import { BoardPage } from "./features/tasks/BoardPage";
import { HomeRedirect } from "./features/teams/HomeRedirect";
import { TeamPage } from "./features/teams/TeamPage";
import { TeamScope } from "./features/teams/TeamScope";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route index element={<HomeRedirect />} />
        <Route path="teams/:teamId" element={<TeamScope />}>
          <Route index element={<BoardPage />} />
          <Route path="archived" element={<ArchivedPage />} />
          <Route path="members" element={<TeamPage />} />
        </Route>
        <Route path="*" element={<p className="p-6 text-slate-700">Page not found.</p>} />
      </Route>
    </Routes>
  );
}

function RequireAuth() {
  const auth = useAuth();
  const location = useLocation();
  if (auth.status === "loading") return <Loading />;
  if (auth.status === "anonymous") {
    // The login page sends the user back here (a link from a notification, a bookmark).
    const from = location.pathname + location.search;
    return <Navigate to="/login" replace state={{ from }} />;
  }
  return <AppLayout />;
}
