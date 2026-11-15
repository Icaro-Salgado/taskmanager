import { useId } from "react";

import { Button } from "../../components/Button";
import { useMembers } from "../teams/queries";
import type { BoardFilters } from "./queries";

interface BoardFiltersBarProps {
  teamId: number;
  filters: BoardFilters;
  onChange: (filters: BoardFilters) => void;
}

const CONTROL = "mt-1 block rounded-md border border-slate-300 bg-white px-2 py-1 text-sm";

/** The filters sent with every column's request. */
export function BoardFiltersBar({ teamId, filters, onChange }: BoardFiltersBarProps) {
  const id = useId();
  const members = useMembers(teamId);
  const isFiltered = Object.values(filters).some((value) => value !== undefined);

  function set(changes: Partial<BoardFilters>) {
    onChange({ ...filters, ...changes });
  }

  return (
    <fieldset className="flex flex-wrap items-end gap-3">
      <legend className="sr-only">Filters</legend>
      <div>
        <label htmlFor={`${id}-assignee`} className="block text-xs font-medium text-slate-600">
          Assignee
        </label>
        <select
          id={`${id}-assignee`}
          value={filters.assignee ?? ""}
          onChange={(event) => set({ assignee: event.target.value || undefined })}
          className={CONTROL}
        >
          <option value="">Anyone</option>
          <option value="none">Unassigned</option>
          {members.data?.map((member) => (
            <option key={member.user_id} value={String(member.user_id)}>
              {member.email}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor={`${id}-after`} className="block text-xs font-medium text-slate-600">
          Due from
        </label>
        <input
          id={`${id}-after`}
          type="date"
          value={filters.due_after ?? ""}
          onChange={(event) => set({ due_after: event.target.value || undefined })}
          className={CONTROL}
        />
      </div>
      <div>
        <label htmlFor={`${id}-before`} className="block text-xs font-medium text-slate-600">
          Due until
        </label>
        <input
          id={`${id}-before`}
          type="date"
          value={filters.due_before ?? ""}
          onChange={(event) => set({ due_before: event.target.value || undefined })}
          className={CONTROL}
        />
      </div>
      <div className="flex items-center gap-2 pb-1.5">
        <input
          id={`${id}-overdue`}
          type="checkbox"
          checked={filters.overdue === true}
          onChange={(event) => set({ overdue: event.target.checked || undefined })}
          className="h-4 w-4"
        />
        <label htmlFor={`${id}-overdue`} className="text-sm text-slate-700">
          Overdue only
        </label>
      </div>
      {isFiltered && (
        <Button variant="ghost" onClick={() => onChange({})}>
          Clear filters
        </Button>
      )}
    </fieldset>
  );
}
