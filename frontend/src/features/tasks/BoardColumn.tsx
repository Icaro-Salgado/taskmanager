import type { TaskStatus } from "../../api/types";
import { Button } from "../../components/Button";
import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { uniqueById } from "../../lib/uniqueById";
import { useStatusColumn, type BoardFilters } from "./queries";
import { TaskCard } from "./TaskCard";

interface BoardColumnProps {
  teamId: number;
  status: TaskStatus;
  label: string;
  filters: BoardFilters;
  onOpenTask: (taskId: number) => void;
}

export function BoardColumn({ teamId, status, label, filters, onOpenTask }: BoardColumnProps) {
  const column = useStatusColumn(teamId, status, filters);
  const headingId = `column-${status}`;
  const total = column.data?.pages[0]?.count;
  const tasks = uniqueById((column.data?.pages ?? []).flatMap((page) => page.results));

  return (
    <section
      aria-labelledby={headingId}
      // relative: the visually hidden labels (absolutely positioned) stay inside the scrolling board
      // instead of widening the page on phones.
      className="relative flex w-[85vw] max-w-sm shrink-0 snap-start flex-col rounded-lg bg-slate-200/70 p-2 sm:w-72 lg:w-auto lg:max-w-none"
    >
      <h2 id={headingId} className="mb-2 flex justify-between px-1 text-sm font-semibold text-slate-700">
        <span>{label}</span>
        {total !== undefined && <span className="text-slate-500">{total}</span>}
      </h2>

      {column.isPending && <Loading />}
      {column.isError && <ErrorMessage error={column.error} />}
      {column.isSuccess && total === 0 && (
        <p className="px-1 py-4 text-center text-sm text-slate-500">No tasks.</p>
      )}

      <ul className="space-y-2">
        {tasks.map((task) => (
          <li key={task.id}>
            <TaskCard task={task} onOpen={() => onOpenTask(task.id)} />
          </li>
        ))}
      </ul>

      {column.hasNextPage && (
        <Button
          variant="ghost"
          className="mt-2 w-full"
          disabled={column.isFetchingNextPage}
          onClick={() => void column.fetchNextPage()}
        >
          {column.isFetchingNextPage ? "Loading…" : "Load more"}
        </Button>
      )}
    </section>
  );
}
