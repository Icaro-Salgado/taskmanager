import type { TaskStatus } from "../../api/types";

/** The API's statuses, in board order, with their labels (backend/apps/tasks/models.py). */
export const STATUSES: { value: TaskStatus; label: string }[] = [
  { value: "todo", label: "To do" },
  { value: "in_progress", label: "In progress" },
  { value: "blocked", label: "Blocked" },
  { value: "done", label: "Done" },
  { value: "canceled", label: "Canceled" },
];

/**
 * Done and canceled are the API's finished (terminal) statuses. The frontend uses this list only to
 * choose which controls to show (a finished task offers reopen instead of edit); the API enforces
 * the rule itself.
 */
const TERMINAL: readonly TaskStatus[] = ["done", "canceled"];

export function isTerminal(status: TaskStatus): boolean {
  return TERMINAL.includes(status);
}

export function statusLabel(status: TaskStatus): string {
  return STATUSES.find((entry) => entry.value === status)?.label ?? status;
}
