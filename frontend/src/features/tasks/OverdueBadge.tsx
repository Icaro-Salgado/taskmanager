/** Shown when the API says the task is overdue (`is_overdue`); never computed here. */
export function OverdueBadge() {
  return (
    <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-800">
      Overdue
    </span>
  );
}
