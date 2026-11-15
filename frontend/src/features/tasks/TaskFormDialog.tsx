import { useState, type FormEvent } from "react";

import type { Task, TaskStatus, Team } from "../../api/types";
import { Button } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import { ErrorMessage } from "../../components/ErrorMessage";
import { SelectField, TextAreaField, TextField } from "../../components/TextField";
import { fieldErrors } from "../../lib/errors";
import { useMembers } from "../teams/queries";
import { useCreateTask, useUpdateTask } from "./queries";
import { isTerminal, STATUSES } from "./statuses";

interface TaskFormDialogProps {
  team: Team;
  /** The task to edit; without it the dialog creates a new task. */
  task?: Task;
  onClose: () => void;
}

/** Create and edit dialog. The API validates every field; its field errors show under each input. */
export function TaskFormDialog({ team, task, onClose }: TaskFormDialogProps) {
  const members = useMembers(team.id);
  const create = useCreateTask();
  const update = useUpdateTask();
  const mutation = task ? update : create;

  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [status, setStatus] = useState<TaskStatus>(task?.status ?? "todo");
  const [assignee, setAssignee] = useState(task?.assignee ? String(task.assignee.id) : "");
  const [dueDate, setDueDate] = useState(task?.due_date ?? "");

  // A task cannot be created finished, so the create form offers only the open statuses.
  const statusOptions = task ? STATUSES : STATUSES.filter((entry) => !isTerminal(entry.value));
  const errors = fieldErrors(mutation.error);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = {
      title,
      description,
      status,
      assignee: assignee ? Number(assignee) : null,
      due_date: dueDate || null,
    };
    if (task) {
      update.mutate({ task, changes: fields }, { onSuccess: onClose });
    } else {
      create.mutate({ team: team.id, ...fields }, { onSuccess: onClose });
    }
  }

  return (
    <Dialog title={task ? "Edit task" : `New task in ${team.name}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-3">
        <TextField
          label="Title"
          required
          maxLength={200}
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          errors={errors.title}
        />
        <TextAreaField
          label="Description"
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          errors={errors.description}
        />
        <div className="grid gap-3 sm:grid-cols-2">
          <SelectField
            label="Status"
            value={status}
            onChange={(event) => setStatus(event.target.value as TaskStatus)}
            errors={errors.status}
          >
            {statusOptions.map((entry) => (
              <option key={entry.value} value={entry.value}>
                {entry.label}
              </option>
            ))}
          </SelectField>
          <TextField
            label="Due date"
            type="date"
            value={dueDate}
            onChange={(event) => setDueDate(event.target.value)}
            errors={errors.due_date}
          />
        </div>
        <SelectField
          label="Assignee"
          value={assignee}
          onChange={(event) => setAssignee(event.target.value)}
          errors={errors.assignee}
        >
          <option value="">Unassigned</option>
          {/* The current assignee stays selectable while the member list loads. */}
          {task?.assignee && !members.data && (
            <option value={String(task.assignee.id)}>{task.assignee.email}</option>
          )}
          {members.data?.map((member) => (
            <option key={member.user_id} value={String(member.user_id)}>
              {member.email}
            </option>
          ))}
        </SelectField>
        {members.isError && <ErrorMessage error={members.error} />}
        {/* The API's message ("Invalid input.", a rule, 403, 404); field errors show above. */}
        <ErrorMessage error={mutation.error} />
        <div className="flex justify-end gap-2 pt-2">
          <Button onClick={onClose}>Cancel</Button>
          <Button type="submit" variant="primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : task ? "Save" : "Create"}
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
