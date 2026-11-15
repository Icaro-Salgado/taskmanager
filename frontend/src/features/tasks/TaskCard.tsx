import { useId } from "react";

import type { Task, TaskStatus } from "../../api/types";
import { useToast } from "../../components/toastContext";
import { errorMessage } from "../../lib/errors";
import { formatDate } from "../../lib/format";
import { useUpdateTask } from "./queries";
import { isTerminal, STATUSES } from "./statuses";
import { OverdueBadge } from "./OverdueBadge";

interface TaskCardProps {
  task: Task;
  onOpen: () => void;
}

export function TaskCard({ task, onOpen }: TaskCardProps) {
  const statusId = useId();
  const toast = useToast();
  const update = useUpdateTask();
  // Finished tasks change only through reopen, in the task detail.
  const canChangeStatus = task.can_edit && !isTerminal(task.status);

  function changeStatus(status: TaskStatus) {
    update.mutate(
      { task, changes: { status } },
      { onError: (error) => toast.show(errorMessage(error)) },
    );
  }

  return (
    <article className="rounded-md bg-white p-3 shadow-sm">
      <button
        type="button"
        onClick={onOpen}
        className="block w-full text-left text-sm font-medium text-slate-900 hover:underline"
      >
        {task.title}
      </button>
      <dl className="mt-2 space-y-1 text-xs text-slate-600">
        <div className="flex gap-1">
          <dt className="sr-only">Assignee</dt>
          <dd className="truncate">{task.assignee ? task.assignee.email : "Unassigned"}</dd>
        </div>
        {task.due_date && (
          <div className="flex items-center gap-2">
            <dt className="sr-only">Due</dt>
            <dd>Due {formatDate(task.due_date)}</dd>
            {task.is_overdue && <OverdueBadge />}
          </div>
        )}
      </dl>
      {canChangeStatus && (
        <div className="mt-2">
          <label htmlFor={statusId} className="sr-only">
            Status of {task.title}
          </label>
          <select
            id={statusId}
            value={task.status}
            disabled={update.isPending}
            onChange={(event) => changeStatus(event.target.value as TaskStatus)}
            className="w-full rounded border border-slate-300 bg-white px-1 py-1 text-xs"
          >
            {STATUSES.map((status) => (
              <option key={status.value} value={status.value}>
                {status.label}
              </option>
            ))}
          </select>
        </div>
      )}
    </article>
  );
}
