/**
 * Keeps the first item of each id. Pages fetched at different moments can overlap when tasks are
 * added or moved in between ("load more" asks by page number), and a repeated item would show
 * twice and break React's keys.
 */
export function uniqueById<T extends { id: number }>(items: T[]): T[] {
  const seen = new Set<number>();
  return items.filter((item) => {
    if (seen.has(item.id)) return false;
    seen.add(item.id);
    return true;
  });
}
