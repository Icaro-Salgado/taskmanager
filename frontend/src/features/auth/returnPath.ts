/** The page RequireAuth sent the user away from, or the home page. Only paths inside the app. */
export function returnPath(state: unknown): string {
  if (typeof state !== "object" || state === null || !("from" in state)) return "/";
  const from = state.from;
  return typeof from === "string" && from.startsWith("/") && !from.startsWith("//") ? from : "/";
}
