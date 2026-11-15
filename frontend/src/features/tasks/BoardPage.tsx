import { useState } from "react";

import { Button } from "../../components/Button";
import { useTeam } from "../teams/teamContext";
import { BoardColumn } from "./BoardColumn";
import { BoardFiltersBar } from "./BoardFiltersBar";
import type { BoardFilters } from "./queries";
import { STATUSES } from "./statuses";
import { TaskDetailDialog } from "./TaskDetailDialog";
import { TaskFormDialog } from "./TaskFormDialog";
import { useOpenTask } from "./useOpenTask";

/** The task board: one column per status, each its own paginated request. */
export function BoardPage() {
  const team = useTeam();
  const [filters, setFilters] = useState<BoardFilters>({});
  const [creating, setCreating] = useState(false);
  const { openTaskId, openTask, closeTask } = useOpenTask();

  return (
    <main className="mx-auto max-w-screen-2xl px-4 py-4">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <BoardFiltersBar teamId={team.id} filters={filters} onChange={setFilters} />
        <Button variant="primary" onClick={() => setCreating(true)}>
          New task
        </Button>
      </div>

      {/* Phones: the columns scroll sideways, one screen-wide column at a time. */}
      <div className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-4 lg:mx-0 lg:grid lg:grid-cols-5 lg:overflow-visible lg:px-0">
        {STATUSES.map((status) => (
          <BoardColumn
            key={status.value}
            teamId={team.id}
            status={status.value}
            label={status.label}
            filters={filters}
            onOpenTask={openTask}
          />
        ))}
      </div>

      {creating && <TaskFormDialog team={team} onClose={() => setCreating(false)} />}
      {openTaskId !== null && (
        <TaskDetailDialog key={openTaskId} taskId={openTaskId} team={team} onClose={closeTask} />
      )}
    </main>
  );
}
