import { NavLink, Outlet, useNavigate, useParams } from "react-router";

import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { useTeams } from "./queries";

const TABS = [
  { to: "", label: "Board", end: true },
  { to: "archived", label: "Archived", end: false },
  { to: "members", label: "Members", end: false },
];

/**
 * Resolves the team in the URL among the teams the user can see (all of them for an admin), shows
 * the team selector and the team's tabs, and hands the team to the page below.
 */
export function TeamScope() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const teams = useTeams();

  if (teams.isPending) return <Loading />;
  if (teams.isError) {
    return (
      <main className="p-4">
        <ErrorMessage error={teams.error} />
      </main>
    );
  }
  const team = teams.data.find((candidate) => String(candidate.id) === teamId);
  if (!team) return <p className="p-6 text-slate-700">Team not found.</p>;

  return (
    <>
      <div className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-screen-2xl flex-wrap items-end gap-x-6 gap-y-2 px-4 py-2">
          <div className="flex items-center gap-2">
            <label htmlFor="team-selector" className="text-sm font-medium text-slate-700">
              Team
            </label>
            <select
              id="team-selector"
              value={team.id}
              onChange={(event) => void navigate(`/teams/${event.target.value}`)}
              className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm"
            >
              {teams.data.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.name}
                </option>
              ))}
            </select>
          </div>
          <nav aria-label="Team pages" className="flex gap-1">
            {TABS.map((tab) => (
              <NavLink
                key={tab.label}
                to={tab.to ? `/teams/${team.id}/${tab.to}` : `/teams/${team.id}`}
                end={tab.end}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm font-medium ${
                    isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"
                  }`
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
      {/* key: a new team starts with fresh page state (filters, open dialogs). */}
      <Outlet key={team.id} context={team} />
    </>
  );
}
