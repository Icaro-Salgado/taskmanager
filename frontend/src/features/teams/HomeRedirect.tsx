import { Navigate } from "react-router";

import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { useTeams } from "./queries";

/** The start page: the board of the first team, or a note when the user has no team. */
export function HomeRedirect() {
  const teams = useTeams();
  if (teams.isPending) return <Loading />;
  if (teams.isError) {
    return (
      <main className="p-4">
        <ErrorMessage error={teams.error} />
      </main>
    );
  }
  const first = teams.data[0];
  if (!first) {
    return (
      <main className="p-6 text-slate-700">
        You are not a member of any team yet. Ask a team leader to add you.
      </main>
    );
  }
  return <Navigate to={`/teams/${first.id}`} replace />;
}
