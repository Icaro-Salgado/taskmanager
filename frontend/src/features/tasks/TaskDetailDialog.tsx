import { useState, type ReactNode } from "react";

import type { Task, Team } from "../../api/types";
import { Button } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { isNotFound } from "../../lib/errors";
import { formatDate, formatDateTime } from "../../lib/format";
import { OverdueBadge } from "./OverdueBadge";
import { useAssignSelf, useDeleteTask, useReopenTask, useTask } from "./queries";
import { isTerminal, statusLabel } from "./statuses";
import { TaskFormDialog } from "./TaskFormDialog";

interface TaskDetailDialogProps {
  taskId: number;
  team: Team;
  onClose: () => void;
}

export function TaskDetailDialog({ taskId, team, onClose }: TaskDetailDialogProps) {
  const task = useTask(taskId);
  const [editing, setEditing] = useState(false);

  if (editing && task.data) {
    return <TaskFormDialog team={team} task={task.data} onClose={() => setEditing(false)} />;
  }

  return (
    <Dialog title={task.data?.title ?? "Task"} onClose={onClose}>
      {task.isPending && <Loading />}
      {task.isError &&
        (isNotFound(task.error) ? (
          <p className="text-sm text-slate-700">
            This task does not exist any more, or you cannot see it.
          </p>
        ) : (
          <ErrorMessage error={task.error} />
        ))}
      {task.data && (
        <TaskDetail
          task={task.data}
          isMember={team.my_role !== null}
          onEdit={() => setEditing(true)}
          onDeleted={onClose}
        />
      )}
    </Dialog>
  );
}

interface TaskDetailProps {
  task: Task;
  /** Admins who are not members of the team cannot take a task. */
  isMember: boolean;
  onEdit: () => void;
  onDeleted: () => void;
}

function TaskDetail({ task, isMember, onEdit, onDeleted }: TaskDetailProps) {
  const reopen = useReopenTask();
  const assignSelf = useAssignSelf();
  const remove = useDeleteTask();
  const finished = isTerminal(task.status);
  const actionError = reopen.error ?? assignSelf.error ?? remove.error;
  const busy = reopen.isPending || assignSelf.isPending || remove.isPending;

  function handleDelete() {
    if (window.confirm(`Delete "${task.title}"?`)) {
      remove.mutate(task.id, { onSuccess: onDeleted });
    }
  }

  return (
    <div className="space-y-4">
      <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-2 text-sm">
        <Row label="Status">{statusLabel(task.status)}</Row>
        <Row label="Assignee">{task.assignee?.email ?? "Unassigned"}</Row>
        <Row label="Due date">
          {task.due_date ? (
            <span className="flex items-center gap-2">
              {formatDate(task.due_date)}
              {task.is_overdue && <OverdueBadge />}
            </span>
          ) : (
            "None"
          )}
        </Row>
        {task.completed_at && <Row label="Finished">{formatDateTime(task.completed_at)}</Row>}
        <Row label="Created by">{task.created_by.email}</Row>
        <Row label="Created">{formatDateTime(task.created_at)}</Row>
        <Row label="Updated">{formatDateTime(task.updated_at)}</Row>
      </dl>
      <div>
        <h3 className="text-sm font-medium text-slate-700">Description</h3>
        <p className="mt-1 text-sm whitespace-pre-wrap text-slate-800">
          {task.description || <span className="text-slate-500">No description.</span>}
        </p>
      </div>

      <ErrorMessage error={actionError} />

      <div className="flex flex-wrap justify-end gap-2 border-t border-slate-200 pt-3">
        {task.can_delete && (
          <Button variant="danger" disabled={busy} onClick={handleDelete}>
            Delete
          </Button>
        )}
        {isMember && !task.assignee && !finished && (
          <Button disabled={busy} onClick={() => assignSelf.mutate(task.id)}>
            Assign to me
          </Button>
        )}
        {task.can_edit && finished && (
          <Button variant="primary" disabled={busy} onClick={() => reopen.mutate(task.id)}>
            Reopen
          </Button>
        )}
        {task.can_edit && !finished && (
          <Button variant="primary" disabled={busy} onClick={onEdit}>
            Edit
          </Button>
        )}
      </div>
    </div>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <>
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-slate-900">{children}</dd>
    </>
  );
}
