/** "2026-03-09" → "Mar 9, 2026", read as a calendar date (no time zone shift). */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  if (!year || !month || !day) return isoDate;
  return new Date(year, month - 1, day).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** The day of an ISO timestamp, in the browser's locale and time zone. */
export function formatDay(isoDateTime: string): string {
  return new Date(isoDateTime).toLocaleDateString(undefined, { dateStyle: "medium" });
}

/** An ISO timestamp from the API in the browser's locale and time zone. */
export function formatDateTime(isoDateTime: string): string {
  return new Date(isoDateTime).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
