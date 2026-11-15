import { useOutletContext } from "react-router";

import type { Team } from "../../api/types";

/** The team of the current page, resolved by TeamScope. */
export function useTeam(): Team {
  return useOutletContext<Team>();
}
