import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { notificationsApi } from "../../api/endpoints";
import { isNotFound } from "../../lib/errors";

/** Notifications are read by polling; the API has no push channel. */
const POLL_MS = 60_000;

export const notificationKeys = {
  all: ["notifications"] as const,
  unreadCount: ["notifications", "unread-count"] as const,
  recent: ["notifications", "recent"] as const,
};

/** Polls every minute, but stops if the endpoint does not exist (404) instead of asking forever. */
function pollInterval(query: { state: { error: unknown } }): number | false {
  return isNotFound(query.state.error) ? false : POLL_MS;
}

/** The number of unread notifications: the count of the unread list, one item fetched. */
export function useUnreadCount() {
  return useQuery({
    queryKey: notificationKeys.unreadCount,
    queryFn: () => notificationsApi.list({ unread: true, page_size: 1 }),
    select: (page) => page.count,
    refetchInterval: pollInterval,
  });
}

/** The latest notifications, read and unread, for the bell's list. */
export function useRecentNotifications(enabled: boolean) {
  return useQuery({
    queryKey: notificationKeys.recent,
    queryFn: () => notificationsApi.list({ page_size: 10 }),
    enabled,
    refetchInterval: pollInterval,
  });
}

export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => notificationsApi.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}
