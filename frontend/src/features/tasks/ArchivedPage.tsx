import { useState } from "react";

import { Button } from "../../components/Button";
import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { formatDateTime } from "../../lib/format";
import { useTeam } from "../teams/teamContext";
import { useArchivedTasks } from "./queries";
import { statusLabel } from "./statuses";
import { TaskDetailDialog } from "./TaskDetailDialog";
import { useOpenTask } from "./useOpenTask";

/** Archived tasks (finished longer ago than the team's archive_after_days), a page at a time. */
export function ArchivedPage() {
  const team = useTeam();
  const [page, setPage] = useState(1);
  const archived = useArchivedTasks(team.id, page);
  const { openTaskId, openTask, closeTask } = useOpenTask();

  return (
    <main className="mx-auto max-w-3xl px-4 py-4">
      <h1 className="text-lg font-semibold text-slate-900">Archived tasks</h1>
      <p className="mb-4 text-sm text-slate-600">
        Tasks finished more than {team.archive_after_days} days ago.
      </p>

      {archived.isPending && <Loading />}
      {archived.isError && <ErrorMessage error={archived.error} />}
      {/* A page can vanish when its last tasks are reopened; the API then answers 404. */}
      {archived.isError && page > 1 && (
        <Button className="mt-2" onClick={() => setPage(1)}>
          Back to the first page
        </Button>
      )}
      {archived.data?.count === 0 && <p className="text-sm text-slate-500">No archived tasks.</p>}

      {archived.data && archived.data.count > 0 && (
        <ul className="divide-y divide-slate-200 rounded-lg bg-white shadow-sm">
          {archived.data.results.map((task) => (
            <li key={task.id} className="flex flex-wrap items-center justify-between gap-2 p-3">
              <button
                type="button"
                onClick={() => openTask(task.id)}
                className="text-left text-sm font-medium text-slate-900 hover:underline"
              >
                {task.title}
              </button>
              <span className="text-xs text-slate-600">
                {statusLabel(task.status)}
                {task.completed_at && ` · ${formatDateTime(task.completed_at)}`}
              </span>
            </li>
          ))}
        </ul>
      )}

      {archived.data && (archived.data.previous || archived.data.next) && (
        <nav aria-label="Pages" className="mt-4 flex items-center justify-between">
          <Button disabled={!archived.data.previous} onClick={() => setPage(page - 1)}>
            Previous
          </Button>
          <span className="text-sm text-slate-600">Page {page}</span>
          <Button
            disabled={!archived.data.next || archived.isPlaceholderData}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </nav>
      )}

      {openTaskId !== null && (
        <TaskDetailDialog key={openTaskId} taskId={openTaskId} team={team} onClose={closeTask} />
      )}
    </main>
  );
}
