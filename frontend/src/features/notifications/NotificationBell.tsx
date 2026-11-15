import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";

import type { Notification } from "../../api/types";
import { ErrorMessage } from "../../components/ErrorMessage";
import { Loading } from "../../components/Loading";
import { isNotFound } from "../../lib/errors";
import { formatDateTime } from "../../lib/format";
import { useMarkRead, useRecentNotifications, useUnreadCount } from "./queries";

/**
 * The bell: the unread count (polled every minute) and a list of recent notifications. Opening one
 * marks it read and, when it is about a task, opens that task.
 */
export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const unread = useUnreadCount();
  const recent = useRecentNotifications(open);
  const markRead = useMarkRead();
  const count = unread.data ?? 0;

  useEffect(() => {
    if (!open) return;
    function closeOnOutsideClick(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", closeOnOutsideClick);
    return () => document.removeEventListener("mousedown", closeOnOutsideClick);
  }, [open]);

  function openNotification(notification: Notification) {
    if (!notification.read_at) markRead.mutate(notification.id);
    setOpen(false);
    const query = notification.task ? `?task=${notification.task}` : "";
    void navigate(`/teams/${notification.team}${query}`);
  }

  return (
    <div
      ref={containerRef}
      className="relative"
      onKeyDown={(event) => {
        if (event.key === "Escape") setOpen(false);
      }}
    >
      <button
        type="button"
        aria-expanded={open}
        aria-controls="notification-list"
        aria-label={count ? `Notifications, ${count} unread` : "Notifications"}
        onClick={() => setOpen(!open)}
        className="relative rounded-md p-2 text-slate-700 hover:bg-slate-100"
      >
        <BellIcon />
        {count > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-5 rounded-full bg-red-600 px-1 text-center text-xs font-semibold text-white">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && (
        <div
          id="notification-list"
          className="absolute right-0 z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] rounded-lg border border-slate-200 bg-white shadow-lg"
        >
          <h2 className="border-b border-slate-200 px-3 py-2 text-sm font-semibold text-slate-900">
            Notifications
          </h2>
          <div className="max-h-96 overflow-y-auto">
            {recent.isPending && <Loading />}
            {recent.isError &&
              (isNotFound(recent.error) ? (
                <p className="p-3 text-sm text-slate-500">Notifications are not available.</p>
              ) : (
                <div className="p-3">
                  <ErrorMessage error={recent.error} />
                </div>
              ))}
            {recent.data?.results.length === 0 && (
              <p className="p-3 text-sm text-slate-500">No notifications.</p>
            )}
            <ul>
              {recent.data?.results.map((notification) => (
                <li key={notification.id} className="border-b border-slate-100 last:border-0">
                  <button
                    type="button"
                    onClick={() => openNotification(notification)}
                    className="flex w-full gap-2 px-3 py-2 text-left hover:bg-slate-50"
                  >
                    <span
                      aria-hidden="true"
                      className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${notification.read_at ? "bg-transparent" : "bg-blue-600"}`}
                    />
                    <span className="min-w-0">
                      <span
                        className={`block text-sm ${notification.read_at ? "text-slate-600" : "font-medium text-slate-900"}`}
                      >
                        {notification.message}
                        {!notification.read_at && <span className="sr-only"> (unread)</span>}
                      </span>
                      <span className="block text-xs text-slate-500">
                        {formatDateTime(notification.created_at)}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

function BellIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}
