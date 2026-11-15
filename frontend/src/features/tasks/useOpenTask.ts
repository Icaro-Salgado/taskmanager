import { useSearchParams } from "react-router";

/**
 * The task shown in the detail dialog lives in the URL (?task=12), so a notification can link to
 * it and the browser's back button closes it.
 */
export function useOpenTask() {
  const [searchParams, setSearchParams] = useSearchParams();
  const value = Number(searchParams.get("task"));
  const openTaskId = Number.isInteger(value) && value > 0 ? value : null;

  return {
    openTaskId,
    openTask: (taskId: number) => setSearchParams({ task: String(taskId) }),
    closeTask: () => setSearchParams({}, { replace: true }),
  };
}
