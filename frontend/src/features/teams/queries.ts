import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { teamsApi } from "../../api/endpoints";
import type { Role, Team } from "../../api/types";

export const teamKeys = {
  all: ["teams"] as const,
  members: (teamId: number) => ["teams", teamId, "members"] as const,
};

export function useTeams() {
  return useQuery({ queryKey: teamKeys.all, queryFn: teamsApi.list });
}

export function useMembers(teamId: number) {
  return useQuery({
    queryKey: teamKeys.members(teamId),
    queryFn: () => teamsApi.members(teamId),
  });
}

/**
 * After any membership change: members and teams (my_role may change) are re-read, and so are
 * tasks, because removing a member unassigns their tasks and a role change alters can_edit.
 */
function useInvalidateAfterMembershipChange() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: teamKeys.all }),
      queryClient.invalidateQueries({ queryKey: ["tasks"] }),
    ]);
}

export function useAddMember(teamId: number) {
  const invalidate = useInvalidateAfterMembershipChange();
  return useMutation({
    mutationFn: (email: string) => teamsApi.addMember(teamId, email),
    onSuccess: invalidate,
  });
}

export function useChangeRole(teamId: number) {
  const invalidate = useInvalidateAfterMembershipChange();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: Role }) =>
      teamsApi.changeRole(teamId, userId, role),
    onSuccess: invalidate,
  });
}

/**
 * The caller leaves the team. The team's queries are dropped rather than re-read: the caller can
 * no longer see the team, so asking again would only answer 404.
 */
export function useLeaveTeam(teamId: number, userId: number, onLeft: () => void) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => teamsApi.removeMember(teamId, userId),
    onSuccess: () => {
      // Drop the team from the cached list first, so the selector never offers it again.
      queryClient.setQueryData<Team[]>(teamKeys.all, (teams) =>
        teams?.filter((team) => team.id !== teamId),
      );
      onLeft();
      queryClient.removeQueries({ queryKey: ["teams", teamId] });
      queryClient.removeQueries({ queryKey: ["tasks"] });
      return queryClient.invalidateQueries({ queryKey: teamKeys.all, exact: true });
    },
  });
}

export function useRemoveMember(teamId: number) {
  const invalidate = useInvalidateAfterMembershipChange();
  return useMutation({
    mutationFn: (userId: number) => teamsApi.removeMember(teamId, userId),
    onSuccess: invalidate,
  });
}
