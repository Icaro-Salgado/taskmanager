import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import type { Member } from "../../api/types";
import { Button } from "../../components/Button";
import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { TextField } from "../../components/TextField";
import { fieldErrors } from "../../lib/errors";
import { formatDay } from "../../lib/format";
import { useCurrentUser } from "../auth/authContext";
import {
  useAddMember,
  useChangeRole,
  useLeaveTeam,
  useMembers,
  useRemoveMember,
} from "./queries";
import { useTeam } from "./teamContext";

/** The team's members. Leaders (and admins) add, promote, demote and remove; anyone can leave. */
export function TeamPage() {
  const team = useTeam();
  const user = useCurrentUser();
  const navigate = useNavigate();
  const members = useMembers(team.id);
  const changeRole = useChangeRole(team.id);
  const removeMember = useRemoveMember(team.id);
  const leave = useLeaveTeam(team.id, user.id, () => void navigate("/", { replace: true }));
  // From the API: the caller's role in this team (null for an admin who is not a member).
  const canManage = team.my_role === "leader" || user.is_admin;
  const busy = changeRole.isPending || removeMember.isPending || leave.isPending;

  function handleRemove(member: Member) {
    if (window.confirm(`Remove ${member.email} from ${team.name}? Their tasks become unassigned.`)) {
      removeMember.mutate(member.user_id);
    }
  }

  function handleLeave() {
    if (window.confirm(`Leave ${team.name}? Your tasks in it become unassigned.`)) {
      leave.mutate();
    }
  }

  return (
    <main className="mx-auto max-w-3xl space-y-4 px-4 py-4">
      <h1 className="text-lg font-semibold text-slate-900">Members of {team.name}</h1>

      {canManage && <AddMemberForm teamId={team.id} />}

      <ErrorMessage error={changeRole.error ?? removeMember.error ?? leave.error} />
      {members.isPending && <Loading />}
      {members.isError && <ErrorMessage error={members.error} />}
      {members.data?.length === 0 && <p className="text-sm text-slate-500">No members.</p>}

      {members.data && members.data.length > 0 && (
        <ul className="divide-y divide-slate-200 rounded-lg bg-white shadow-sm">
          {members.data.map((member) => {
            const isMe = member.user_id === user.id;
            return (
              <li key={member.user_id} className="flex flex-wrap items-center gap-3 p-3">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-slate-900">
                    {member.email}
                    {isMe && " (you)"}
                  </p>
                  <p className="text-xs text-slate-600">
                    {member.role === "leader" ? "Leader" : "Member"} · joined{" "}
                    {formatDay(member.joined_at)}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {canManage && (
                    <Button
                      disabled={busy}
                      onClick={() =>
                        changeRole.mutate({
                          userId: member.user_id,
                          role: member.role === "leader" ? "member" : "leader",
                        })
                      }
                    >
                      {member.role === "leader" ? "Make member" : "Make leader"}
                    </Button>
                  )}
                  {isMe ? (
                    <Button variant="danger" disabled={busy} onClick={handleLeave}>
                      Leave team
                    </Button>
                  ) : (
                    canManage && (
                      <Button variant="danger" disabled={busy} onClick={() => handleRemove(member)}>
                        Remove
                      </Button>
                    )
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}

function AddMemberForm({ teamId }: { teamId: number }) {
  const [email, setEmail] = useState("");
  const add = useAddMember(teamId);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    add.mutate(email.trim(), { onSuccess: () => setEmail("") });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2 rounded-lg bg-white p-3 shadow-sm">
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-0 flex-1">
          <TextField
            label="Add a member by email"
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            errors={fieldErrors(add.error).email}
          />
        </div>
        <Button type="submit" variant="primary" disabled={add.isPending}>
          Add
        </Button>
      </div>
      <ErrorMessage error={add.error} />
    </form>
  );
}
