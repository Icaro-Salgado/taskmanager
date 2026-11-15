import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";

import { tasksApi } from "../../api/endpoints";
import type { Task, TaskCreate, TaskListParams, TaskStatus, TaskUpdate } from "../../api/types";
import { useToast } from "../../components/toastContext";
import { errorMessage } from "../../lib/errors";
import { isTerminal, statusLabel } from "./statuses";

export const taskKeys = {
  all: ["tasks"] as const,
  lists: ["tasks", "list"] as const,
  list: (params: TaskListParams) => ["tasks", "list", params] as const,
  detail: (taskId: number) => ["tasks", "detail", taskId] as const,
};

/** The filters the board applies to every column. */
export interface BoardFilters {
  assignee?: string;
  due_after?: string;
  due_before?: string;
  overdue?: boolean;
}

/** One board column: the tasks of one status, a page at a time ("load more"). */
export function useStatusColumn(teamId: number, status: TaskStatus, filters: BoardFilters) {
  const params: TaskListParams = { team: teamId, status, ...filters };
  return useInfiniteQuery({
    queryKey: taskKeys.list(params),
    queryFn: ({ pageParam, signal }) =>
      tasksApi.list({ ...params, page: pageParam }, signal),
    initialPageParam: 1,
    getNextPageParam: (lastPage, pages) => (lastPage.next ? pages.length + 1 : undefined),
  });
}

/** Archived tasks of a team, as a plain list one page at a time. */
export function useArchivedTasks(teamId: number, page: number) {
  return useQuery({
    queryKey: taskKeys.list({ team: teamId, archived: true, page }),
    queryFn: ({ signal }) => tasksApi.list({ team: teamId, archived: true, page }, signal),
    // Keep showing the current page while the next one loads.
    placeholderData: keepPreviousData,
  });
}

export function useTask(taskId: number) {
  return useQuery({
    queryKey: taskKeys.detail(taskId),
    queryFn: ({ signal }) => tasksApi.get(taskId, signal),
  });
}

/** Stores the task the API answered and re-reads every list, whose columns may have changed. */
function refreshAfterChange(queryClient: QueryClient, task: Task) {
  queryClient.setQueryData(taskKeys.detail(task.id), task);
  return queryClient.invalidateQueries({ queryKey: taskKeys.lists });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TaskCreate) => tasksApi.create(data),
    onSuccess: (task) => refreshAfterChange(queryClient, task),
  });
}

export function useReopenTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: number) => tasksApi.reopen(taskId),
    onSuccess: (task) => refreshAfterChange(queryClient, task),
  });
}

/**
 * Edits a task. When the change finishes it (done or canceled), a toast offers Undo for a few
 * seconds, which reopens the task.
 */
export function useUpdateTask() {
  const queryClient = useQueryClient();
  const toast = useToast();
  return useMutation({
    mutationFn: ({ task, changes }: { task: Task; changes: TaskUpdate }) =>
      tasksApi.update(task.id, changes),
    onSuccess: (updated, { task: before }) => {
      if (isTerminal(updated.status) && !isTerminal(before.status)) {
        // A plain call, not a mutation hook: the toast outlives the card or dialog that made the
        // change, and the query client and toast it uses live for the whole app.
        const undo = () =>
          tasksApi
            .reopen(updated.id)
            .then((task) => refreshAfterChange(queryClient, task))
            .catch((error: unknown) => toast.show(errorMessage(error)));
        toast.show(`"${updated.title}" moved to ${statusLabel(updated.status)}.`, {
          durationMs: 6000,
          action: { label: "Undo", onClick: () => void undo() },
        });
      }
      return refreshAfterChange(queryClient, updated);
    },
  });
}

export function useAssignSelf() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: number) => tasksApi.assignSelf(taskId),
    onSuccess: (task) => refreshAfterChange(queryClient, task),
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: number) => tasksApi.remove(taskId),
    onSuccess: (_result, taskId) => {
      queryClient.removeQueries({ queryKey: taskKeys.detail(taskId) });
      return queryClient.invalidateQueries({ queryKey: taskKeys.lists });
    },
  });
}
